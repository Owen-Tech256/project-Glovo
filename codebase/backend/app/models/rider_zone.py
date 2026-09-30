import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class RiderZoneStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class RiderZone(db.Model, PublicIdMixin, TimestampMixin):
    """A rider's declared operating eligibility in one of Phase 2's branch
    delivery zones (SRS 6: "Allow riders to have one or more operating
    zones"). Reuses `DeliveryZone` as-is - no new geography model - so
    zone coverage logic (`DeliveryZone.covers()`, app/catalog/geo.py) stays
    in exactly one place for both customer discovery and rider dispatch."""

    __tablename__ = "rider_zones"

    id = db.Column(db.Integer, primary_key=True)
    rider_id = db.Column(db.Integer, db.ForeignKey("riders.id", ondelete="CASCADE"), nullable=False, index=True)
    delivery_zone_id = db.Column(
        db.Integer, db.ForeignKey("delivery_zones.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status = db.Column(
        db.Enum(RiderZoneStatus, name="rider_zone_status", native_enum=False, length=20),
        nullable=False,
        default=RiderZoneStatus.ACTIVE,
        index=True,
    )

    delivery_zone = db.relationship("DeliveryZone")

    __table_args__ = (
        db.UniqueConstraint("rider_id", "delivery_zone_id", name="uq_rider_zones_rider_zone"),
    )

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "zone_id": self.delivery_zone.public_id if self.delivery_zone else None,
            "zone_name": self.delivery_zone.name if self.delivery_zone else None,
            "branch_id": self.delivery_zone.branch.public_id
            if self.delivery_zone and self.delivery_zone.branch else None,
            "branch_name": self.delivery_zone.branch.name
            if self.delivery_zone and self.delivery_zone.branch else None,
            "status": self.status.value if isinstance(self.status, RiderZoneStatus) else self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<RiderZone rider_id={self.rider_id} zone_id={self.delivery_zone_id}>"
