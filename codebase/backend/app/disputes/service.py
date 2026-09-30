"""
Dispute lifecycle (SRS 6). `resolve_with_refund` is the one place a
dispute action ever touches money, and it only ever does so by calling
into app.payments.refund_service - never by editing a balance/ledger row
directly (SRS 6/14).
"""
import secrets
from datetime import datetime, timezone
from decimal import Decimal

from app.extensions import db
from app.common.errors import NotFoundError, ValidationAppError, AuthorizationError
from app.models.user import User, UserRole
from app.models.order import Order
from app.models.dispute import Dispute, DisputeCategory, DisputePriority, DisputeStatus
from app.models.dispute_evidence import DisputeEvidence
from app.models.dispute_action import DisputeAction, DisputeActionType, DisputeActionStatus
from app.rbac.service import has_permission


def _is_staff_viewer(user: User) -> bool:
    return user.role == UserRole.ADMIN and (has_permission(user, "disputes.view") or has_permission(user, "disputes.manage") or has_permission(user, "disputes.financial_action"))


def _is_staff_manager(user: User) -> bool:
    return user.role == UserRole.ADMIN and has_permission(user, "disputes.manage")


def _order_touches_user(order: Order, user: User) -> bool:
    if order.customer_id == user.id:
        return True
    if user.role == UserRole.VENDOR and order.branch.vendor.user_id == user.id:
        return True
    if user.role == UserRole.RIDER and order.delivery and order.delivery.rider and order.delivery.rider.user_id == user.id:
        return True
    return False


def _generate_dispute_number() -> str:
    return f"DSP-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(4).upper()}"


def _unique_dispute_number() -> str:
    for _ in range(5):
        candidate = _generate_dispute_number()
        if Dispute.query.filter_by(dispute_number=candidate).first() is None:
            return candidate
    return f"DSP-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{secrets.token_hex(6).upper()}"


def create_dispute(opened_by: User, order_public_id: str, category: str, description: str,
                    delivery_public_id: str | None = None, payment_public_id: str | None = None,
                    refund_public_id: str | None = None, ticket_public_id: str | None = None) -> Dispute:
    order = Order.query.filter_by(public_id=order_public_id).first()
    if order is None:
        raise NotFoundError("Order not found.")
    if not _order_touches_user(order, opened_by):
        raise AuthorizationError("You cannot open a dispute for an order that isn't yours.")

    delivery_id = None
    if delivery_public_id:
        from app.models.delivery import Delivery

        delivery = Delivery.query.filter_by(public_id=delivery_public_id, order_id=order.id).first()
        if delivery is None:
            raise NotFoundError("Delivery not found on this order.")
        delivery_id = delivery.id
    elif order.delivery:
        delivery_id = order.delivery.id

    payment_id = None
    if payment_public_id:
        from app.models.payment import Payment

        payment = Payment.query.filter_by(public_id=payment_public_id, order_id=order.id).first()
        if payment is None:
            raise NotFoundError("Payment not found on this order.")
        payment_id = payment.id

    refund_id = None
    if refund_public_id:
        from app.models.refund import Refund

        refund = Refund.query.filter_by(public_id=refund_public_id, order_id=order.id).first()
        if refund is None:
            raise NotFoundError("Refund not found on this order.")
        refund_id = refund.id

    ticket_id = None
    if ticket_public_id:
        from app.support.service import get_ticket_for_requester_or_404

        ticket = get_ticket_for_requester_or_404(opened_by, ticket_public_id)
        if ticket.dispute is not None:
            raise ValidationAppError("This ticket already has a dispute.", code="TICKET_ALREADY_DISPUTED")
        ticket_id = ticket.id

    dispute = Dispute(
        dispute_number=_unique_dispute_number(),
        ticket_id=ticket_id, order_id=order.id, delivery_id=delivery_id, payment_id=payment_id, refund_id=refund_id,
        opened_by=opened_by.id, category=DisputeCategory(category), priority=DisputePriority.NORMAL,
        status=DisputeStatus.OPEN, description=description,
    )
    db.session.add(dispute)
    db.session.flush()
    db.session.commit()

    from app.audit.service import record

    record(opened_by, "DISPUTE_OPENED", entity_type="DISPUTE", entity_id=dispute.public_id,
           after={"order": order.public_id, "category": category})
    return dispute


def get_dispute_for_user_or_404(user: User, dispute_public_id: str) -> Dispute:
    dispute = Dispute.query.filter_by(public_id=dispute_public_id).first()
    if dispute is None:
        raise NotFoundError("Dispute not found.")
    if not _order_touches_user(dispute.order, user):
        raise AuthorizationError()
    return dispute


def get_any_dispute_or_404(dispute_public_id: str) -> Dispute:
    dispute = Dispute.query.filter_by(public_id=dispute_public_id).first()
    if dispute is None:
        raise NotFoundError("Dispute not found.")
    return dispute


def list_disputes_for_user(user: User, page: int = 1, per_page: int = 20):
    from app.models.branch import Branch
    from app.models.vendor import Vendor
    from app.models.delivery import Delivery
    from app.models.rider import Rider

    if user.role == UserRole.CUSTOMER:
        query = Dispute.query.join(Order).filter(Order.customer_id == user.id)
    elif user.role == UserRole.VENDOR:
        query = Dispute.query.join(Order).join(Branch, Order.branch_id == Branch.id).join(Vendor).filter(Vendor.user_id == user.id)
    else:
        query = (
            Dispute.query.join(Order).join(Delivery, Order.id == Delivery.order_id)
            .join(Rider, Delivery.rider_id == Rider.id).filter(Rider.user_id == user.id)
        )
    return query.order_by(Dispute.created_at.desc()).paginate(
        page=max(page, 1), per_page=max(min(per_page, 100), 1), error_out=False
    )


def list_all_disputes(status: str | None = None, category: str | None = None, priority: str | None = None,
                       page: int = 1, per_page: int = 20):
    query = Dispute.query
    if status:
        query = query.filter(Dispute.status == status)
    if category:
        query = query.filter(Dispute.category == category)
    if priority:
        query = query.filter(Dispute.priority == priority)
    return query.order_by(Dispute.priority.desc(), Dispute.created_at.asc()).paginate(
        page=max(page, 1), per_page=max(min(per_page, 100), 1), error_out=False
    )


def add_evidence(user: User, dispute: Dispute, evidence_type: str, secure_reference: str | None = None,
                  description: str | None = None) -> DisputeEvidence:
    if not _order_touches_user(dispute.order, user) and not _is_staff_viewer(user):
        raise AuthorizationError()
    evidence = DisputeEvidence(
        dispute_id=dispute.id, submitted_by=user.id, evidence_type=evidence_type,
        secure_reference=secure_reference, description=description,
    )
    db.session.add(evidence)
    db.session.commit()
    return evidence


def update_status(actor: User, dispute: Dispute, status: str, resolution: str | None = None) -> Dispute:
    from app.models.base import _utcnow

    before_status = dispute.status.value
    new_status = DisputeStatus(status)
    dispute.status = new_status
    if resolution is not None:
        dispute.resolution = resolution
    if new_status in (DisputeStatus.RESOLVED, DisputeStatus.REJECTED, DisputeStatus.CLOSED):
        dispute.resolved_by = actor.id
        dispute.resolved_at = _utcnow()
    db.session.commit()

    from app.audit.service import record

    record(actor, "DISPUTE_STATUS_CHANGED", entity_type="DISPUTE", entity_id=dispute.public_id,
           before={"status": before_status}, after={"status": new_status.value})
    _notify_customer(dispute, f"Dispute {dispute.dispute_number} {new_status.value.lower()}", resolution)
    return dispute


def record_action(actor: User, dispute: Dispute, action_type: str, reason: str | None = None) -> DisputeAction:
    if not _is_staff_manager(actor):
        raise AuthorizationError("Only staff with dispute-management permission can record dispute actions.")
    action_type_enum = DisputeActionType(action_type)
    action = DisputeAction(
        dispute_id=dispute.id, action_type=action_type_enum, actor_id=actor.id, reason=reason,
        status=DisputeActionStatus.COMPLETED,
    )
    db.session.add(action)
    if dispute.status == DisputeStatus.OPEN:
        dispute.status = DisputeStatus.INVESTIGATING
    db.session.commit()

    from app.audit.service import record

    record(actor, "DISPUTE_ACTION_RECORDED", entity_type="DISPUTE", entity_id=dispute.public_id,
           after={"action_type": action_type, "reason": reason})
    return action


def resolve_with_refund(actor: User, dispute: Dispute, amount: Decimal | None, reason: str) -> DisputeAction:
    """The only place in app/disputes/ that moves money - always through
    app.payments.refund_service, which itself validates the order has a
    successful payment and enforces the refundable-amount ceiling under a
    row lock. `amount=None` means "refund whatever remains refundable"."""
    if not has_permission(actor, "disputes.financial_action"):
        raise AuthorizationError("Only staff with dispute financial-action permission can resolve a dispute with a refund.")

    from app.payments import refund_service
    from app.models.refund import RefundStatus

    order = dispute.order
    idempotency_key = f"dispute:{dispute.public_id}"
    try:
        refund, _created = refund_service.request_refund(order.customer, order.public_id, amount, reason, idempotency_key)
        if refund.status == RefundStatus.REQUESTED:
            refund = refund_service.approve_refund(actor, refund)
        action_type = DisputeActionType.PARTIAL_REFUND_ISSUED if (amount is not None and amount < order.total) else DisputeActionType.REFUND_ISSUED
        action_status = DisputeActionStatus.COMPLETED if refund.status == RefundStatus.SUCCEEDED else DisputeActionStatus.FAILED
    except Exception as exc:  # noqa: BLE001 - recorded as a FAILED action, then re-raised
        db.session.rollback()
        action = DisputeAction(
            dispute_id=dispute.id, action_type=DisputeActionType.OTHER, actor_id=actor.id,
            reference_type="REFUND", reason=f"Refund attempt failed: {exc}", status=DisputeActionStatus.FAILED,
        )
        db.session.add(action)
        db.session.commit()
        raise

    dispute.refund_id = refund.id
    action = DisputeAction(
        dispute_id=dispute.id, action_type=action_type, actor_id=actor.id,
        reference_type="REFUND", reference_id=refund.public_id, reason=reason, status=action_status,
    )
    db.session.add(action)
    db.session.commit()

    from app.audit.service import record

    record(actor, "DISPUTE_RESOLVED_WITH_REFUND", entity_type="DISPUTE", entity_id=dispute.public_id,
           after={"refund_id": refund.public_id, "refund_status": refund.status.value, "amount": str(refund.amount)})
    return action


def _notify_customer(dispute: Dispute, title: str, body: str | None) -> None:
    from app.notifications.events import notify
    from app.models.notification import NotificationCategory

    notify(
        dispute.order.customer, NotificationCategory.DISPUTE, title=title,
        body=body or f"There is an update on dispute {dispute.dispute_number}.",
        entity_type="DISPUTE", entity_id=dispute.public_id,
    )
