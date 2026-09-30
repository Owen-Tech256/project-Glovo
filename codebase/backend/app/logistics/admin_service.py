"""
Admin-side logistics oversight (SRS 5, 9, 13): rider onboarding
verification, document review, delivery monitoring, and authorized
reassignment/intervention. Every state-changing action here writes an
`AuditEvent` (the same Phase 1 audit table auth/service.py uses) so
administrative intervention is always auditable, per SRS 13.
"""
from datetime import timedelta

from flask import current_app

from app.extensions import db
from app.common.errors import NotFoundError, ValidationAppError
from app.models.rider import Rider, RiderOnboardingStatus, RiderOperationalStatus
from app.models.rider_document import RiderDocument, RiderDocumentVerificationStatus
from app.models.delivery import Delivery, DeliveryStatus
from app.models.delivery_assignment import DeliveryAssignmentStatus
from app.models.delivery_status_history import DeliveryStatusHistory
from app.models.audit_event import AuditEvent
from app.logistics import state_machine as delivery_state_machine
from app.logistics import dispatch_service
from app.logistics import rider_service
from app.logistics.helpers import get_rider_by_public_id_or_404, get_any_delivery_or_404, utcnow

# Structurally valid onboarding-status transitions an admin may make.
_ONBOARDING_TRANSITIONS: dict[RiderOnboardingStatus, set[RiderOnboardingStatus]] = {
    RiderOnboardingStatus.PENDING: {RiderOnboardingStatus.UNDER_REVIEW, RiderOnboardingStatus.REJECTED},
    RiderOnboardingStatus.UNDER_REVIEW: {RiderOnboardingStatus.APPROVED, RiderOnboardingStatus.REJECTED},
    RiderOnboardingStatus.APPROVED: {RiderOnboardingStatus.SUSPENDED},
    RiderOnboardingStatus.REJECTED: {RiderOnboardingStatus.UNDER_REVIEW},
    RiderOnboardingStatus.SUSPENDED: {RiderOnboardingStatus.APPROVED, RiderOnboardingStatus.REJECTED},
}


def _audit(admin_user, event_type: str, ip_address: str | None, note: str | None = None) -> None:
    db.session.add(
        AuditEvent(user_id=admin_user.id, event_type=event_type, ip_address=ip_address, user_agent=(note or "")[:255])
    )


# --- Rider verification -----------------------------------------------------

def list_riders(onboarding_status: str | None = None, page: int = 1, per_page: int = 20):
    query = Rider.query
    if onboarding_status:
        query = query.filter(Rider.onboarding_status == onboarding_status)
    return query.order_by(Rider.created_at.desc()).paginate(
        page=max(page, 1), per_page=max(min(per_page, 100), 1), error_out=False
    )


def get_rider_or_404(rider_public_id: str) -> Rider:
    return get_rider_by_public_id_or_404(rider_public_id)


def set_onboarding_status(admin_user, rider_public_id: str, new_status: str, reason: str | None, ip_address: str | None) -> Rider:
    rider = get_rider_by_public_id_or_404(rider_public_id)
    target = RiderOnboardingStatus(new_status)
    allowed = _ONBOARDING_TRANSITIONS.get(rider.onboarding_status, set())
    if target not in allowed:
        raise ValidationAppError(
            f"Cannot move a rider from {rider.onboarding_status.value} to {target.value}.",
            code="INVALID_TRANSITION",
        )

    rider.onboarding_status = target
    if target == RiderOnboardingStatus.APPROVED:
        rider.approved_at = utcnow()

    # A rider who is no longer APPROVED can no longer be online (SRS 5:
    # "Only approved operational riders are dispatch-eligible"). This phase
    # does not auto-reassign an in-flight delivery a suspended/rejected
    # rider might already be carrying - see PHASE_4_NOTES.md; an admin
    # uses reassign_delivery separately for that.
    if target != RiderOnboardingStatus.APPROVED and rider.operational_status != RiderOperationalStatus.OFFLINE:
        rider_service._record_availability_change(rider, RiderOperationalStatus.OFFLINE, f"Onboarding set to {target.value}.")

    _audit(admin_user, f"RIDER_ONBOARDING_{target.value}", ip_address, reason)
    db.session.commit()
    return rider


def list_rider_documents(rider_public_id: str) -> list[RiderDocument]:
    rider = get_rider_by_public_id_or_404(rider_public_id)
    return rider.documents.all()


def review_document(admin_user, rider_public_id: str, document_public_id: str, verification_status: str,
                     review_notes: str | None, ip_address: str | None) -> RiderDocument:
    rider = get_rider_by_public_id_or_404(rider_public_id)
    document = rider.documents.filter_by(public_id=document_public_id).first()
    if document is None:
        raise NotFoundError("Document not found.")

    document.verification_status = RiderDocumentVerificationStatus(verification_status)
    document.reviewed_by = admin_user.id
    document.reviewed_at = utcnow()
    document.review_notes = review_notes

    _audit(admin_user, f"RIDER_DOCUMENT_{document.verification_status.value}", ip_address, review_notes)
    db.session.commit()
    return document


# --- Delivery monitoring + intervention -------------------------------------

def get_dispatch_health() -> dict:
    """Phase 9: aggregate status visibility into the automated dispatch
    engine (app/logistics/dispatch_service.py) - not a control surface,
    since dispatch parameters (batch size, offer expiry, candidate cap)
    are static app config, not admin-editable rows. "Stuck" means still
    SEARCHING/OFFERED past DISPATCH_STUCK_THRESHOLD_SECONDS after the
    delivery was created, i.e. dispatch has had a full opportunity to
    find and exhaust a candidate and hasn't resolved it either way."""
    threshold = utcnow() - timedelta(
        seconds=current_app.config.get("DISPATCH_STUCK_THRESHOLD_SECONDS", 180)
    )
    searching = Delivery.query.filter(Delivery.status == DeliveryStatus.SEARCHING).count()
    offered = Delivery.query.filter(Delivery.status == DeliveryStatus.OFFERED).count()
    stuck_query = Delivery.query.filter(
        Delivery.status.in_([DeliveryStatus.SEARCHING, DeliveryStatus.OFFERED]),
        Delivery.created_at <= threshold,
    )
    stuck_count = stuck_query.count()
    stuck_preview = stuck_query.order_by(Delivery.created_at).limit(20).all()
    return {
        "searching_count": searching,
        "offered_count": offered,
        "stuck_count": stuck_count,
        "stuck_threshold_seconds": current_app.config.get("DISPATCH_STUCK_THRESHOLD_SECONDS", 180),
        "stuck_deliveries": [d.to_public_dict() for d in stuck_preview],
    }


def list_deliveries(status: str | None = None, branch_public_id: str | None = None,
                     rider_public_id: str | None = None, page: int = 1, per_page: int = 20):
    from app.models.branch import Branch

    query = Delivery.query
    if status:
        query = query.filter(Delivery.status == status)
    if branch_public_id:
        query = query.join(Branch, Delivery.branch_id == Branch.id).filter(Branch.public_id == branch_public_id)
    if rider_public_id:
        query = query.join(Rider, Delivery.rider_id == Rider.id).filter(Rider.public_id == rider_public_id)
    return query.order_by(Delivery.created_at.desc()).paginate(
        page=max(page, 1), per_page=max(min(per_page, 100), 1), error_out=False
    )


def get_delivery_or_404(delivery_public_id: str) -> Delivery:
    return get_any_delivery_or_404(delivery_public_id)


REASSIGNABLE_STATES = {DeliveryStatus.CREATED, DeliveryStatus.SEARCHING, DeliveryStatus.OFFERED, DeliveryStatus.ASSIGNED}


def reassign_delivery(admin_user, delivery_public_id: str, reason: str | None, ip_address: str | None) -> Delivery:
    """Cancels any pending offers, frees the currently-assigned rider (if
    any), and retries dispatch excluding that rider - the "authorized
    reassignment/intervention" SRS 9 calls for. Also doubles as a manual
    "retry dispatch" lever for a delivery stuck SEARCHING with zero
    candidates, since this stack has no background scheduler to retry it
    automatically."""
    delivery = get_any_delivery_or_404(delivery_public_id)
    if delivery.status not in REASSIGNABLE_STATES:
        raise ValidationAppError(
            f"A delivery in {delivery.status.value} cannot be reassigned.", code="NOT_REASSIGNABLE"
        )

    now = utcnow()
    pending = delivery.assignments.filter_by(status=DeliveryAssignmentStatus.OFFERED).all()
    for assignment in pending:
        assignment.status = DeliveryAssignmentStatus.CANCELLED
        assignment.responded_at = now

    previous_rider = delivery.rider
    exclude_ids = set()
    if previous_rider is not None:
        exclude_ids.add(previous_rider.id)
        if previous_rider.operational_status == RiderOperationalStatus.BUSY:
            rider_service._record_availability_change(previous_rider, RiderOperationalStatus.AVAILABLE, "Reassigned by admin.")
        delivery.rider_id = None
        delivery.assigned_at = None

    if delivery.status != DeliveryStatus.SEARCHING:
        delivery_state_machine.apply_transition(
            delivery, DeliveryStatus.SEARCHING, actor_user=admin_user, reason=reason or "Reassigned by admin."
        )
    else:
        db.session.add(
            DeliveryStatusHistory(
                delivery_id=delivery.id, from_status=DeliveryStatus.SEARCHING.value,
                to_status=DeliveryStatus.SEARCHING.value, changed_by_user_id=admin_user.id,
                reason=reason or "Dispatch retried by admin.",
            )
        )

    dispatch_service.attempt_dispatch(delivery, extra_exclude_rider_ids=exclude_ids)

    _audit(admin_user, "DELIVERY_REASSIGNED", ip_address, reason)
    db.session.commit()
    return delivery


def get_delivery_status_history(delivery: Delivery):
    return delivery.status_history.all()
