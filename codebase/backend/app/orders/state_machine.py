"""
Server-side order state machine (SRS 6.4). Every transition anywhere in the
app - the Phase 3 payment placeholder, a vendor's prep-workflow action, a
customer cancellation, or a Phase 4 logistics event - goes through
`apply_transition()` below, so `order_status_history` is guaranteed
complete and no code path can move an order directly from field assignment.

    CREATED -> PENDING_PAYMENT -> PAYMENT_CONFIRMED -> VENDOR_ACCEPTED -> PREPARING -> READY
        -> RIDER_ASSIGNED -> PICKED_UP -> DELIVERING -> DELIVERED

Cancellation is a controlled side path available only from the "early"
states (before a vendor has started preparing the order). Once an order is
READY, Phase 4 owns everything past it (see app/logistics/); there is no
customer-cancel path once a rider is in the loop, matching the PREPARING ->
READY step's own no-cancellation stance from Phase 3.
"""
from app.extensions import db
from app.common.errors import ValidationAppError, AuthorizationError
from app.models.order import OrderStatus
from app.models.order_status_history import OrderStatusHistory

# The full set of structurally valid next-states for each status. This is
# the outer boundary - actor-specific rules (below) are always a subset.
TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.CREATED: {OrderStatus.PENDING_PAYMENT, OrderStatus.CANCELLED},
    OrderStatus.PENDING_PAYMENT: {OrderStatus.PAYMENT_CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.PAYMENT_CONFIRMED: {OrderStatus.VENDOR_ACCEPTED, OrderStatus.CANCELLED},
    OrderStatus.VENDOR_ACCEPTED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.READY},
    OrderStatus.READY: {OrderStatus.RIDER_ASSIGNED},
    OrderStatus.RIDER_ASSIGNED: {OrderStatus.PICKED_UP},
    OrderStatus.PICKED_UP: {OrderStatus.DELIVERING},
    OrderStatus.DELIVERING: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}

# The subset of transitions a RIDER actor may trigger, via the delivery
# pickup/start/complete actions in app/logistics/delivery_service.py.
# READY -> RIDER_ASSIGNED is deliberately excluded here: that step is
# system-driven by the dispatch engine the instant an offer is accepted,
# not a direct rider action (see apply_transition() calls in
# app/logistics/dispatch_service.py).
RIDER_TRANSITIONS: dict[OrderStatus, OrderStatus] = {
    OrderStatus.RIDER_ASSIGNED: OrderStatus.PICKED_UP,
    OrderStatus.PICKED_UP: OrderStatus.DELIVERING,
    OrderStatus.DELIVERING: OrderStatus.DELIVERED,
}

# States from which a customer-initiated cancellation is still allowed.
# Once a vendor has started preparing the order, cancellation is no longer
# offered in this phase (no refund/compensation engine exists yet).
CANCELLABLE_STATES = {
    OrderStatus.CREATED,
    OrderStatus.PENDING_PAYMENT,
    OrderStatus.PAYMENT_CONFIRMED,
    OrderStatus.VENDOR_ACCEPTED,
}

# The subset of transitions a VENDOR actor may trigger via
# POST /vendor/orders/{id}/transition. Payment placeholder transitions and
# cancellation are deliberately excluded - a vendor accepts, prepares, and
# marks ready; it does not touch payment state or cancel on the customer's
# behalf.
VENDOR_TRANSITIONS: dict[OrderStatus, OrderStatus] = {
    OrderStatus.PAYMENT_CONFIRMED: OrderStatus.VENDOR_ACCEPTED,
    OrderStatus.VENDOR_ACCEPTED: OrderStatus.PREPARING,
    OrderStatus.PREPARING: OrderStatus.READY,
}


def apply_transition(order, to_status: OrderStatus, actor_user=None, reason: str | None = None) -> OrderStatusHistory:
    """Validates and performs a single transition, recording it. Does not
    commit - callers control the transaction boundary (a checkout's
    system-driven placeholder transitions and the order-creation history
    row all belong in the same commit)."""
    from_status = order.status
    allowed = TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise ValidationAppError(
            f"Cannot move an order from {from_status.value} to {to_status.value}.",
            code="INVALID_TRANSITION",
        )

    order.status = to_status
    history = OrderStatusHistory(
        order_id=order.id,
        from_status=from_status.value,
        to_status=to_status.value,
        changed_by_user_id=actor_user.id if actor_user else None,
        reason=reason,
    )
    db.session.add(history)
    return history


def apply_vendor_transition(order, to_status: OrderStatus, vendor_user, reason: str | None = None) -> OrderStatusHistory:
    """Narrower than `apply_transition`: only the specific forward steps a
    vendor is permitted to make (see VENDOR_TRANSITIONS)."""
    expected_next = VENDOR_TRANSITIONS.get(order.status)
    if expected_next is None or to_status != expected_next:
        raise ValidationAppError(
            f"Vendors cannot move an order from {order.status.value} to {to_status.value}.",
            code="INVALID_TRANSITION",
        )
    return apply_transition(order, to_status, actor_user=vendor_user, reason=reason)


def apply_rider_transition(order, to_status: OrderStatus, rider_user, reason: str | None = None) -> OrderStatusHistory:
    """Narrower than `apply_transition`: only the specific forward steps a
    rider is permitted to make (see RIDER_TRANSITIONS)."""
    expected_next = RIDER_TRANSITIONS.get(order.status)
    if expected_next is None or to_status != expected_next:
        raise ValidationAppError(
            f"Riders cannot move an order from {order.status.value} to {to_status.value}.",
            code="INVALID_TRANSITION",
        )
    return apply_transition(order, to_status, actor_user=rider_user, reason=reason)


def apply_cancellation(order, actor_user, reason: str) -> OrderStatusHistory:
    if order.status not in CANCELLABLE_STATES:
        raise ValidationAppError(
            f"This order can no longer be cancelled (current status: {order.status.value}).",
            code="NOT_CANCELLABLE",
        )
    from datetime import datetime, timezone

    history = apply_transition(order, OrderStatus.CANCELLED, actor_user=actor_user, reason=reason)
    order.cancelled_at = datetime.now(timezone.utc)
    order.cancellation_reason = reason
    return history


def require_vendor_owns_order(order, vendor) -> None:
    if order.branch.vendor_id != vendor.id:
        raise AuthorizationError("This order does not belong to one of your branches.")
