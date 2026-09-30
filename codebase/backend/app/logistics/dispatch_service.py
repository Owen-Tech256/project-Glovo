"""
The dispatch engine (SRS 8). Three responsibilities live here, deliberately
kept out of any route handler (SRS 6: "Implement dispatch as a service, not
route-handler logic"):

1. `create_delivery_and_dispatch` - turns a READY order into a Delivery and
   starts the search. Idempotent: calling it twice for the same order
   returns the same row instead of creating a second one.
2. `find_candidates` / `attempt_dispatch` - the candidate pipeline
   (approval, availability, freshness, zone eligibility, not already
   offered/assigned elsewhere) plus the isolated ranking strategy
   (app/logistics/ranking.py), which together create an expiring offer
   batch.
3. `accept_offer` / `reject_offer` / `sweep_expired_offers` - the offer
   lifecycle, including the row-locking that guarantees exactly one rider
   can ever claim a given delivery even if several accept at once.
"""
from datetime import timedelta

from flask import current_app
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.common.errors import NotFoundError, ValidationAppError, ConflictError
from app.models.delivery import Delivery, DeliveryStatus
from app.models.delivery_assignment import DeliveryAssignment, DeliveryAssignmentStatus
from app.models.delivery_status_history import DeliveryStatusHistory
from app.models.rider import Rider, RiderOnboardingStatus, RiderOperationalStatus
from app.models.rider_zone import RiderZoneStatus
from app.models.delivery_zone import DeliveryZone, DeliveryZoneStatus
from app.models.order import OrderStatus
from app.logistics import state_machine as delivery_state_machine
from app.logistics import rider_service
from app.logistics.ranking import default_strategy
from app.logistics.helpers import utcnow, location_freshness_cutoff
from app.models.base import to_aware_utc
from app.orders import state_machine as order_state_machine


# --- Delivery creation (idempotent) ---------------------------------------

def create_delivery_and_dispatch(order) -> tuple[Delivery, bool]:
    """Returns (delivery, was_created). Called the instant a vendor marks
    an order READY (see app/orders/service.py:vendor_transition_order)."""
    existing = Delivery.query.filter_by(order_id=order.id).first()
    if existing is not None:
        return existing, False

    branch = order.branch
    address = order.address_snapshot
    if address is None:
        # Cannot happen through the normal Phase 3 checkout path (every
        # order gets a snapshot at creation) - guarded defensively anyway.
        raise ValidationAppError("This order has no delivery address on file.", code="MISSING_ADDRESS")

    delivery = Delivery(
        order_id=order.id,
        branch_id=branch.id,
        status=DeliveryStatus.CREATED,
        pickup_latitude=branch.latitude,
        pickup_longitude=branch.longitude,
        destination_latitude=address.latitude,
        destination_longitude=address.longitude,
    )
    db.session.add(delivery)
    try:
        db.session.flush()  # obtain delivery.id
    except IntegrityError:
        db.session.rollback()
        existing = Delivery.query.filter_by(order_id=order.id).first()
        if existing is not None:
            return existing, False
        raise

    db.session.add(
        DeliveryStatusHistory(
            delivery_id=delivery.id, from_status=None, to_status=DeliveryStatus.CREATED.value,
            reason="Delivery created for a READY order.",
        )
    )
    delivery_state_machine.apply_transition(
        delivery, DeliveryStatus.SEARCHING, actor_user=None, reason="Dispatch search started."
    )
    attempt_dispatch(delivery)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing = Delivery.query.filter_by(order_id=order.id).first()
        if existing is not None:
            return existing, False
        raise

    return delivery, True


# --- Candidate selection + ranking -----------------------------------------

def _currently_offered_rider_ids() -> set[int]:
    """Riders with a live (unexpired) OFFERED assignment anywhere. Excluded
    from new offer batches so a rider is never juggling two simultaneous
    delivery offers at once."""
    now = utcnow()
    rows = (
        DeliveryAssignment.query.with_entities(DeliveryAssignment.rider_id)
        .filter(DeliveryAssignment.status == DeliveryAssignmentStatus.OFFERED, DeliveryAssignment.expires_at > now)
        .all()
    )
    return {row[0] for row in rows}


def find_candidates(delivery: Delivery, extra_exclude_rider_ids: set[int] | None = None) -> list[Rider]:
    """SRS 8: "Find riders who are approved, online/available, zone-eligible,
    not already assigned and location-fresh." Zone eligibility and
    freshness both go through the same primitives customer discovery
    already uses (DeliveryZone.covers, app/catalog/geo.py), so "rider is
    allowed to work this delivery" and "customer is inside this branch's
    service area" are never two different notions of coverage."""
    max_candidates = current_app.config.get("DISPATCH_MAX_CANDIDATES", 50)

    # Riders already offered (or previously offered and already
    # rejected/expired) THIS delivery are never re-offered it again.
    already_considered = {a.rider_id for a in delivery.assignments}
    exclude_ids = already_considered | _currently_offered_rider_ids() | (extra_exclude_rider_ids or set())

    query = Rider.query.filter(
        Rider.onboarding_status == RiderOnboardingStatus.APPROVED,
        Rider.operational_status == RiderOperationalStatus.AVAILABLE,
        Rider.location_updated_at.isnot(None),
        Rider.location_updated_at >= location_freshness_cutoff(),
    )
    if exclude_ids:
        query = query.filter(~Rider.id.in_(exclude_ids))

    riders = query.limit(max_candidates).all()
    if not riders:
        return []

    eligible: list[Rider] = []
    for rider in riders:
        active_zone_ids = [
            rz.delivery_zone_id for rz in rider.zones.filter_by(status=RiderZoneStatus.ACTIVE).all()
        ]
        if not active_zone_ids:
            continue
        zones = DeliveryZone.query.filter(
            DeliveryZone.id.in_(active_zone_ids), DeliveryZone.status == DeliveryZoneStatus.ACTIVE
        ).all()
        if any(zone.covers(float(delivery.pickup_latitude), float(delivery.pickup_longitude)) for zone in zones):
            eligible.append(rider)

    return eligible


def attempt_dispatch(delivery: Delivery, extra_exclude_rider_ids: set[int] | None = None) -> bool:
    """Ranks candidates and creates a fresh offer batch if the delivery is
    actively searching with no live offers outstanding. Does not commit -
    callers control the transaction boundary. Returns True if a new offer
    batch was created."""
    if delivery.status != DeliveryStatus.SEARCHING:
        return False
    if delivery.rider_id is not None:
        return False
    if delivery.assignments.filter_by(status=DeliveryAssignmentStatus.OFFERED).first() is not None:
        return False

    candidates = find_candidates(delivery, extra_exclude_rider_ids)
    if not candidates:
        return False

    ranked = default_strategy().rank(
        candidates, float(delivery.pickup_latitude), float(delivery.pickup_longitude)
    )
    batch_size = current_app.config.get("DISPATCH_OFFER_BATCH_SIZE", 3)
    batch = ranked[:batch_size]

    now = utcnow()
    expires_at = now + timedelta(seconds=current_app.config.get("DELIVERY_OFFER_EXPIRY_SECONDS", 45))
    for rider in batch:
        db.session.add(
            DeliveryAssignment(
                delivery_id=delivery.id, rider_id=rider.id, status=DeliveryAssignmentStatus.OFFERED,
                offered_at=now, expires_at=expires_at,
            )
        )
    delivery_state_machine.apply_transition(
        delivery, DeliveryStatus.OFFERED, actor_user=None,
        reason=f"Offered to {len(batch)} candidate rider(s).",
    )
    return True


# --- Offer lifecycle ---------------------------------------------------------

def sweep_expired_offers() -> int:
    """Flips every past-due OFFERED assignment to EXPIRED and, for any
    delivery left with no live offers as a result, walks it back to
    SEARCHING and immediately retries dispatch (SRS 8: "Reject/expiry
    returns delivery to dispatchable state"). Called lazily from the rider
    offer-list endpoint and before accept/reject, since this stack has no
    background scheduler - see PHASE_4_NOTES.md."""
    now = utcnow()
    stale = DeliveryAssignment.query.filter(
        DeliveryAssignment.status == DeliveryAssignmentStatus.OFFERED, DeliveryAssignment.expires_at <= now
    ).all()
    if not stale:
        return 0

    affected_delivery_ids: set[int] = set()
    for assignment in stale:
        assignment.status = DeliveryAssignmentStatus.EXPIRED
        assignment.responded_at = now
        affected_delivery_ids.add(assignment.delivery_id)

    for delivery_id in affected_delivery_ids:
        delivery = db.session.get(Delivery, delivery_id)
        if delivery is None or delivery.rider_id is not None:
            continue
        if delivery.assignments.filter_by(status=DeliveryAssignmentStatus.OFFERED).first() is not None:
            continue
        if delivery.status == DeliveryStatus.OFFERED:
            delivery_state_machine.apply_transition(
                delivery, DeliveryStatus.SEARCHING, actor_user=None, reason="All offers expired."
            )
        attempt_dispatch(delivery)

    db.session.commit()
    return len(stale)


def _get_owned_offer_or_404(rider, assignment_public_id: str) -> DeliveryAssignment:
    assignment = DeliveryAssignment.query.filter_by(public_id=assignment_public_id, rider_id=rider.id).first()
    if assignment is None:
        raise NotFoundError("Delivery offer not found.")
    return assignment


def list_offers_for_rider(rider) -> list[DeliveryAssignment]:
    sweep_expired_offers()
    now = utcnow()
    return (
        DeliveryAssignment.query.filter(
            DeliveryAssignment.rider_id == rider.id,
            DeliveryAssignment.status == DeliveryAssignmentStatus.OFFERED,
            DeliveryAssignment.expires_at > now,
        )
        .order_by(DeliveryAssignment.offered_at.desc())
        .all()
    )


def accept_offer(rider, assignment_public_id: str) -> Delivery:
    sweep_expired_offers()
    assignment = _get_owned_offer_or_404(rider, assignment_public_id)

    # Row-lock the parent delivery: this is the serialization point that
    # guarantees exactly one of several concurrently-offered riders can
    # ever win (SRS 8). On SQLite (test suite) with_for_update is a no-op,
    # same documented tradeoff as app/orders/service.py's cart lock - the
    # sequential re-check immediately below is what the tests exercise.
    delivery = Delivery.query.filter_by(id=assignment.delivery_id).with_for_update().first()
    if delivery is None:
        raise NotFoundError("Delivery not found.")

    now = utcnow()
    if assignment.status != DeliveryAssignmentStatus.OFFERED or to_aware_utc(assignment.expires_at) <= now:
        raise ConflictError("This delivery offer is no longer available.", code="OFFER_UNAVAILABLE")
    if delivery.status != DeliveryStatus.OFFERED or delivery.rider_id is not None:
        raise ConflictError("This delivery has already been claimed by another rider.", code="DELIVERY_ALREADY_CLAIMED")
    if not rider.is_dispatch_eligible or rider.operational_status != RiderOperationalStatus.AVAILABLE:
        raise ValidationAppError("You are not currently eligible to accept deliveries.", code="NOT_DISPATCH_ELIGIBLE")

    assignment.status = DeliveryAssignmentStatus.ACCEPTED
    assignment.responded_at = now

    other_offers = DeliveryAssignment.query.filter(
        DeliveryAssignment.delivery_id == delivery.id,
        DeliveryAssignment.id != assignment.id,
        DeliveryAssignment.status == DeliveryAssignmentStatus.OFFERED,
    ).all()
    for other in other_offers:
        other.status = DeliveryAssignmentStatus.CANCELLED
        other.responded_at = now

    delivery.rider_id = rider.id
    delivery.assigned_at = now
    delivery_state_machine.apply_transition(
        delivery, DeliveryStatus.ASSIGNED, actor_user=rider.user, reason="Offer accepted."
    )

    if rider.current_latitude is not None and rider.current_longitude is not None:
        # Seed tracking with the rider's already-known position immediately
        # on assignment, rather than waiting for their next location ping -
        # the customer/vendor should see *something* the instant a rider is
        # assigned, not just after the rider's app happens to ping again.
        from app.models.delivery_location import DeliveryLocation

        db.session.add(
            DeliveryLocation(
                delivery_id=delivery.id, rider_id=rider.id,
                latitude=rider.current_latitude, longitude=rider.current_longitude, recorded_at=now,
            )
        )

    rider_service._record_availability_change(rider, RiderOperationalStatus.BUSY, "Accepted a delivery.")

    order = delivery.order
    order_state_machine.apply_transition(
        order, OrderStatus.RIDER_ASSIGNED, actor_user=None, reason="Rider assigned by dispatch."
    )

    db.session.commit()

    from app.notifications.events import notify
    from app.models.notification import NotificationCategory

    notify(
        order.customer, NotificationCategory.DELIVERY, template_key="rider_assigned",
        context={"order_number": order.public_order_number},
        entity_type="ORDER", entity_id=order.public_id,
    )
    return delivery


def reject_offer(rider, assignment_public_id: str, reason: str | None) -> None:
    sweep_expired_offers()
    assignment = _get_owned_offer_or_404(rider, assignment_public_id)
    if assignment.status != DeliveryAssignmentStatus.OFFERED:
        raise ValidationAppError("This delivery offer is no longer available.", code="OFFER_UNAVAILABLE")

    now = utcnow()
    assignment.status = DeliveryAssignmentStatus.REJECTED
    assignment.responded_at = now
    assignment.rejection_reason = reason

    delivery = db.session.get(Delivery, assignment.delivery_id)
    remaining = delivery.assignments.filter_by(status=DeliveryAssignmentStatus.OFFERED).count()
    if remaining == 0 and delivery.rider_id is None:
        if delivery.status == DeliveryStatus.OFFERED:
            delivery_state_machine.apply_transition(
                delivery, DeliveryStatus.SEARCHING, actor_user=rider.user, reason="Offer rejected by rider."
            )
        attempt_dispatch(delivery)

    db.session.commit()
