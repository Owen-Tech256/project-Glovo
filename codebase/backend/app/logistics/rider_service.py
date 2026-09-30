"""
Rider self-service: everything a RIDER-role user manages about their own
profile - vehicle, documents, operating zones, availability and location.
Dispatch-facing concerns (candidate selection, offers) live in
dispatch_service.py; this module only ever touches the acting rider's own
rows, which is what keeps every route in rider_routes.py a one-line
ownership story ("it's always g.current_user's Rider").
"""
from flask import current_app

from app.extensions import db
from app.common.errors import NotFoundError, ValidationAppError, ConflictError, RateLimitedError
from app.models.rider import Rider, RiderOperationalStatus
from app.models.rider_vehicle import RiderVehicle, RiderVehicleType
from app.models.rider_document import RiderDocument, RiderDocumentType
from app.models.rider_availability_history import RiderAvailabilityHistory
from app.models.rider_location import RiderLocation
from app.models.rider_zone import RiderZone, RiderZoneStatus
from app.models.delivery_zone import DeliveryZone
from app.models.delivery import Delivery, DeliveryStatus
from app.models.delivery_location import DeliveryLocation
from app.logistics.helpers import utcnow, is_location_fresh


# --- Vehicle (upserted via PATCH /rider/profile) --------------------------

def upsert_vehicle(rider: Rider, vehicle_type: str, registration_reference: str | None) -> RiderVehicle:
    vehicle = rider.vehicle
    if vehicle is None:
        vehicle = RiderVehicle(rider_id=rider.id)
        db.session.add(vehicle)
    vehicle.vehicle_type = RiderVehicleType(vehicle_type)
    vehicle.registration_reference = registration_reference
    db.session.commit()
    return vehicle


# --- Documents --------------------------------------------------------------

def add_document(rider: Rider, document_type: str, reference: str, expiry_date) -> RiderDocument:
    document = RiderDocument(
        rider_id=rider.id,
        document_type=RiderDocumentType(document_type),
        reference=reference,
        expiry_date=expiry_date,
    )
    db.session.add(document)
    db.session.commit()
    return document


def list_documents(rider: Rider) -> list[RiderDocument]:
    return rider.documents.all()


# --- Operating zones ---------------------------------------------------------

def list_rider_zones(rider: Rider) -> list[RiderZone]:
    return rider.zones.filter_by(status=RiderZoneStatus.ACTIVE).all()


def join_zone(rider: Rider, zone_public_id: str) -> RiderZone:
    zone = DeliveryZone.query.filter_by(public_id=zone_public_id).first()
    if zone is None:
        raise NotFoundError("Delivery zone not found.")

    existing = RiderZone.query.filter_by(rider_id=rider.id, delivery_zone_id=zone.id).first()
    if existing is not None:
        if existing.status == RiderZoneStatus.ACTIVE:
            return existing
        existing.status = RiderZoneStatus.ACTIVE
        db.session.commit()
        return existing

    rider_zone = RiderZone(rider_id=rider.id, delivery_zone_id=zone.id, status=RiderZoneStatus.ACTIVE)
    db.session.add(rider_zone)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise ConflictError("You are already registered for this zone.", code="ZONE_ALREADY_JOINED")
    return rider_zone


def leave_zone(rider: Rider, zone_public_id: str) -> None:
    zone = DeliveryZone.query.filter_by(public_id=zone_public_id).first()
    if zone is None:
        raise NotFoundError("Delivery zone not found.")
    rider_zone = RiderZone.query.filter_by(rider_id=rider.id, delivery_zone_id=zone.id).first()
    if rider_zone is None:
        raise NotFoundError("You are not registered for this zone.")
    rider_zone.status = RiderZoneStatus.INACTIVE
    db.session.commit()


# --- Availability -------------------------------------------------------------

def get_availability_history(rider: Rider, limit: int = 20) -> list[RiderAvailabilityHistory]:
    return rider.availability_history.limit(limit).all()


def _has_active_delivery(rider: Rider) -> bool:
    return (
        Delivery.query.filter(
            Delivery.rider_id == rider.id,
            Delivery.status.in_([DeliveryStatus.ASSIGNED, DeliveryStatus.PICKED_UP, DeliveryStatus.DELIVERING]),
        ).first()
        is not None
    )


def set_availability(rider: Rider, new_status: str, reason: str | None) -> Rider:
    target = RiderOperationalStatus(new_status)
    current = rider.operational_status

    if target == current:
        return rider

    if target == RiderOperationalStatus.AVAILABLE:
        if not rider.is_dispatch_eligible:
            raise ValidationAppError(
                "Only approved riders can go online.", code="NOT_DISPATCH_ELIGIBLE"
            )
        if current == RiderOperationalStatus.BUSY:
            raise ValidationAppError(
                "You cannot switch to available while a delivery is in progress.", code="RIDER_BUSY"
            )

    if target == RiderOperationalStatus.OFFLINE and current == RiderOperationalStatus.BUSY:
        raise ValidationAppError(
            "You cannot go offline while a delivery is in progress.", code="RIDER_BUSY"
        )

    _record_availability_change(rider, target, reason)
    db.session.commit()
    return rider


def _record_availability_change(rider: Rider, target: RiderOperationalStatus, reason: str | None) -> None:
    """Applies the operational_status change and writes the history row.
    Does not commit - callers control the transaction boundary so a
    system-driven change (e.g. dispatch acceptance) can be committed
    alongside the delivery/order changes it belongs with."""
    from_status = rider.operational_status
    rider.operational_status = target
    db.session.add(
        RiderAvailabilityHistory(
            rider_id=rider.id,
            from_status=from_status.value if hasattr(from_status, "value") else from_status,
            to_status=target.value,
            reason=reason,
        )
    )


# --- Location -----------------------------------------------------------------

def record_location(rider: Rider, latitude: float, longitude: float, accuracy_meters: float | None) -> RiderLocation:
    min_interval = current_app.config.get("RIDER_LOCATION_MIN_INTERVAL_SECONDS", 3)
    if rider.location_updated_at is not None:
        from app.models.base import to_aware_utc

        elapsed = (utcnow() - to_aware_utc(rider.location_updated_at)).total_seconds()
        if elapsed < min_interval:
            raise RateLimitedError(
                f"Location updates are limited to one every {min_interval} seconds.", code="LOCATION_RATE_LIMITED"
            )

    now = utcnow()
    location = RiderLocation(
        rider_id=rider.id, latitude=latitude, longitude=longitude, accuracy_meters=accuracy_meters, recorded_at=now,
    )
    db.session.add(location)

    rider.current_latitude = latitude
    rider.current_longitude = longitude
    rider.location_updated_at = now

    # Also mirror the ping into delivery_locations if this rider currently
    # has a live delivery, so customer/vendor tracking (SRS 9) has
    # up-to-date data without a second API call from the rider app.
    active_delivery = Delivery.query.filter(
        Delivery.rider_id == rider.id,
        Delivery.status.in_([DeliveryStatus.ASSIGNED, DeliveryStatus.PICKED_UP, DeliveryStatus.DELIVERING]),
    ).first()
    if active_delivery is not None:
        db.session.add(
            DeliveryLocation(
                delivery_id=active_delivery.id, rider_id=rider.id,
                latitude=latitude, longitude=longitude, accuracy_meters=accuracy_meters, recorded_at=now,
            )
        )

    db.session.commit()
    return location


def get_current_location(rider: Rider) -> dict:
    return {
        "latitude": float(rider.current_latitude) if rider.current_latitude is not None else None,
        "longitude": float(rider.current_longitude) if rider.current_longitude is not None else None,
        "recorded_at": rider.location_updated_at.isoformat() if rider.location_updated_at else None,
        "is_fresh": is_location_fresh(rider.location_updated_at),
    }
