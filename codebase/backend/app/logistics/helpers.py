"""
Ownership-resolution helpers shared across the logistics service modules,
mirroring app/vendors/helpers.py's role in Phase 2/3: every lookup here is
the one place that decides whether a given user may reach a given row, so
no route handler can accidentally skip an ownership check by querying a
model directly.
"""
from datetime import datetime, timedelta, timezone

from flask import current_app

from app.extensions import db
from app.models.rider import Rider
from app.models.delivery import Delivery
from app.common.errors import NotFoundError


def get_or_create_rider(user) -> Rider:
    """Every RIDER-role user gets exactly one Rider profile, provisioned
    lazily on first access - same pattern as get_or_create_vendor."""
    rider = Rider.query.filter_by(user_id=user.id).first()
    if rider is None:
        rider = Rider(user_id=user.id)
        db.session.add(rider)
        db.session.commit()
    return rider


def get_rider_by_public_id_or_404(rider_public_id: str) -> Rider:
    rider = Rider.query.filter_by(public_id=rider_public_id).first()
    if rider is None:
        raise NotFoundError("Rider not found.")
    return rider


def get_owned_delivery_or_404_for_rider(rider: Rider, delivery_public_id: str) -> Delivery:
    delivery = Delivery.query.filter_by(public_id=delivery_public_id, rider_id=rider.id).first()
    if delivery is None:
        raise NotFoundError("Delivery not found.")
    return delivery


def get_delivery_for_branch_or_404(vendor, delivery_public_id: str) -> Delivery:
    from app.models.branch import Branch

    delivery = (
        Delivery.query.join(Branch, Delivery.branch_id == Branch.id)
        .filter(Delivery.public_id == delivery_public_id, Branch.vendor_id == vendor.id)
        .first()
    )
    if delivery is None:
        raise NotFoundError("Delivery not found.")
    return delivery


def get_any_delivery_or_404(delivery_public_id: str) -> Delivery:
    delivery = Delivery.query.filter_by(public_id=delivery_public_id).first()
    if delivery is None:
        raise NotFoundError("Delivery not found.")
    return delivery


def utcnow():
    return datetime.now(timezone.utc)


def location_freshness_cutoff():
    freshness_seconds = current_app.config.get("RIDER_LOCATION_FRESHNESS_SECONDS", 120)
    return utcnow() - timedelta(seconds=freshness_seconds)


def is_location_fresh(location_updated_at) -> bool:
    if location_updated_at is None:
        return False
    from app.models.base import to_aware_utc

    return to_aware_utc(location_updated_at) >= location_freshness_cutoff()
