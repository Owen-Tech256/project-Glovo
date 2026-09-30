from app.extensions import db
from app.models.base import _utcnow


class RiderLocation(db.Model):
    """Append-only ping history for a rider's own current position, used
    for freshness checks (SRS 7) and general position history - distinct
    from `delivery_locations`, which is the subset of pings scoped to (and
    exposed for tracking on) one specific active delivery. Every accepted
    ping here also updates the denormalized `Rider.current_latitude` /
    `current_longitude` / `location_updated_at` used by dispatch - see
    app/logistics/location_service.py."""

    __tablename__ = "rider_locations"

    id = db.Column(db.Integer, primary_key=True)
    rider_id = db.Column(db.Integer, db.ForeignKey("riders.id", ondelete="CASCADE"), nullable=False, index=True)

    latitude = db.Column(db.Numeric(9, 6), nullable=False)
    longitude = db.Column(db.Numeric(9, 6), nullable=False)
    accuracy_meters = db.Column(db.Numeric(8, 2), nullable=True)

    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)

    __table_args__ = (
        db.CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_rider_locations_latitude_range"),
        db.CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_rider_locations_longitude_range"),
        db.Index("ix_rider_locations_rider_recorded", "rider_id", "recorded_at"),
    )

    def to_public_dict(self) -> dict:
        return {
            "latitude": float(self.latitude) if self.latitude is not None else None,
            "longitude": float(self.longitude) if self.longitude is not None else None,
            "accuracy_meters": float(self.accuracy_meters) if self.accuracy_meters is not None else None,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<RiderLocation rider_id={self.rider_id} ({self.latitude}, {self.longitude})>"
