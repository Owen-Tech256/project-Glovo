from app.extensions import db
from app.models.base import _utcnow


class DeliveryLocation(db.Model):
    """Rider location pings scoped to one specific active delivery - the
    subset of a rider's movement that customer/vendor tracking is allowed
    to see (SRS 9: "Customers retrieve only their own active delivery
    status/latest permitted location"). Written alongside (not instead of)
    `rider_locations` whenever the reporting rider currently has an
    ASSIGNED/PICKED_UP/DELIVERING delivery - see
    app/logistics/location_service.py."""

    __tablename__ = "delivery_locations"

    id = db.Column(db.Integer, primary_key=True)
    delivery_id = db.Column(
        db.Integer, db.ForeignKey("deliveries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rider_id = db.Column(db.Integer, db.ForeignKey("riders.id", ondelete="CASCADE"), nullable=False, index=True)

    latitude = db.Column(db.Numeric(9, 6), nullable=False)
    longitude = db.Column(db.Numeric(9, 6), nullable=False)
    accuracy_meters = db.Column(db.Numeric(8, 2), nullable=True)

    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)

    __table_args__ = (
        db.CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_delivery_locations_latitude_range"),
        db.CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_delivery_locations_longitude_range"),
        db.Index("ix_delivery_locations_delivery_recorded", "delivery_id", "recorded_at"),
    )

    def to_public_dict(self) -> dict:
        return {
            "latitude": float(self.latitude) if self.latitude is not None else None,
            "longitude": float(self.longitude) if self.longitude is not None else None,
            "accuracy_meters": float(self.accuracy_meters) if self.accuracy_meters is not None else None,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<DeliveryLocation delivery_id={self.delivery_id} ({self.latitude}, {self.longitude})>"
