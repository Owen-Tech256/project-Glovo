"""
Server-side delivery state machine (SRS 9), the Phase 4 counterpart of
app/orders/state_machine.py. Every transition - dispatch starting a search,
an offer being accepted, a rider's pickup/start/complete action, or an
admin cancellation - goes through `apply_transition()` so
`delivery_status_history` is always a complete, reconstructable audit
trail.

    CREATED -> SEARCHING -> OFFERED -> ASSIGNED -> PICKED_UP -> DELIVERING -> DELIVERED

CANCELLED is a controlled side path (dispatch exhausted every candidate, or
an admin called it off) available from every non-terminal state.
"""
from app.extensions import db
from app.common.errors import ValidationAppError
from app.models.delivery import DeliveryStatus
from app.models.delivery_status_history import DeliveryStatusHistory

TRANSITIONS: dict[DeliveryStatus, set[DeliveryStatus]] = {
    DeliveryStatus.CREATED: {DeliveryStatus.SEARCHING, DeliveryStatus.CANCELLED},
    DeliveryStatus.SEARCHING: {DeliveryStatus.OFFERED, DeliveryStatus.CANCELLED},
    DeliveryStatus.OFFERED: {DeliveryStatus.ASSIGNED, DeliveryStatus.SEARCHING, DeliveryStatus.CANCELLED},
    DeliveryStatus.ASSIGNED: {DeliveryStatus.PICKED_UP, DeliveryStatus.SEARCHING, DeliveryStatus.CANCELLED},
    DeliveryStatus.PICKED_UP: {DeliveryStatus.DELIVERING},
    DeliveryStatus.DELIVERING: {DeliveryStatus.DELIVERED},
    DeliveryStatus.DELIVERED: set(),
    DeliveryStatus.CANCELLED: set(),
}

# The subset of transitions a RIDER actor may trigger directly, via the
# pickup/start/complete actions in app/logistics/delivery_service.py.
RIDER_TRANSITIONS: dict[DeliveryStatus, DeliveryStatus] = {
    DeliveryStatus.ASSIGNED: DeliveryStatus.PICKED_UP,
    DeliveryStatus.PICKED_UP: DeliveryStatus.DELIVERING,
    DeliveryStatus.DELIVERING: DeliveryStatus.DELIVERED,
}

# States from which dispatch is still "in progress" and can be walked back
# to SEARCHING (an offer expired/was rejected, or an admin reassigns).
REDISPATCHABLE_STATES = {DeliveryStatus.OFFERED, DeliveryStatus.ASSIGNED}

# States from which an admin may cancel a delivery outright.
CANCELLABLE_STATES = {
    DeliveryStatus.CREATED,
    DeliveryStatus.SEARCHING,
    DeliveryStatus.OFFERED,
    DeliveryStatus.ASSIGNED,
}


def apply_transition(delivery, to_status: DeliveryStatus, actor_user=None, reason: str | None = None) -> DeliveryStatusHistory:
    """Validates and performs a single transition, recording it. Does not
    commit - callers control the transaction boundary."""
    from_status = delivery.status
    allowed = TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise ValidationAppError(
            f"Cannot move a delivery from {from_status.value} to {to_status.value}.",
            code="INVALID_TRANSITION",
        )

    delivery.status = to_status
    history = DeliveryStatusHistory(
        delivery_id=delivery.id,
        from_status=from_status.value,
        to_status=to_status.value,
        changed_by_user_id=actor_user.id if actor_user else None,
        reason=reason,
    )
    db.session.add(history)
    return history


def apply_rider_transition(delivery, to_status: DeliveryStatus, rider_user, reason: str | None = None) -> DeliveryStatusHistory:
    expected_next = RIDER_TRANSITIONS.get(delivery.status)
    if expected_next is None or to_status != expected_next:
        raise ValidationAppError(
            f"Cannot move this delivery from {delivery.status.value} to {to_status.value}.",
            code="INVALID_TRANSITION",
        )
    return apply_transition(delivery, to_status, actor_user=rider_user, reason=reason)


def apply_cancellation(delivery, actor_user, reason: str) -> DeliveryStatusHistory:
    if delivery.status not in CANCELLABLE_STATES:
        raise ValidationAppError(
            f"This delivery can no longer be cancelled (current status: {delivery.status.value}).",
            code="NOT_CANCELLABLE",
        )
    from datetime import datetime, timezone

    history = apply_transition(delivery, DeliveryStatus.CANCELLED, actor_user=actor_user, reason=reason)
    delivery.cancelled_at = datetime.now(timezone.utc)
    delivery.cancellation_reason = reason
    return history
