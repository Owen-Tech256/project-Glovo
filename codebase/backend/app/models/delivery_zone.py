import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class DeliveryZoneStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class DeliveryZoneType(str, enum.Enum):
    RADIUS = "RADIUS"
    POLYGON = "POLYGON"


class DeliveryZone(db.Model, PublicIdMixin, TimestampMixin):
    __tablename__ = "delivery_zones"

    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True)

    name = db.Column(db.String(150), nullable=False)
    status = db.Column(
        db.Enum(DeliveryZoneStatus, name="delivery_zone_status", native_enum=False, length=20),
        nullable=False,
        default=DeliveryZoneStatus.ACTIVE,
        index=True,
    )

    # Geographic service-area data. `zone_type` selects the strategy (see
    # app/catalog/geo.py). Today only RADIUS is implemented; the RADIUS
    # columns are nullable so a future POLYGON zone can leave them unset.
    zone_type = db.Column(
        db.Enum(DeliveryZoneType, name="delivery_zone_type", native_enum=False, length=20),
        nullable=False,
        default=DeliveryZoneType.RADIUS,
    )
    center_latitude = db.Column(db.Numeric(9, 6), nullable=True)
    center_longitude = db.Column(db.Numeric(9, 6), nullable=True)
    radius_meters = db.Column(db.Integer, nullable=True)
    # Reserved for a future POLYGON implementation - unused today.
    polygon_geojson = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.CheckConstraint(
            "center_latitude IS NULL OR (center_latitude >= -90 AND center_latitude <= 90)",
            name="ck_delivery_zones_center_latitude_range",
        ),
        db.CheckConstraint(
            "center_longitude IS NULL OR (center_longitude >= -180 AND center_longitude <= 180)",
            name="ck_delivery_zones_center_longitude_range",
        ),
        db.CheckConstraint(
            "radius_meters IS NULL OR radius_meters > 0", name="ck_delivery_zones_radius_positive"
        ),
        db.Index("ix_delivery_zones_branch_status", "branch_id", "status"),
    )

    @property
    def is_active(self) -> bool:
        return self.status == DeliveryZoneStatus.ACTIVE

    def covers(self, latitude: float, longitude: float) -> bool:
        from app.catalog.geo import build_service_area

        return build_service_area(self).covers(latitude, longitude)

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "branch_id": self.branch.public_id if self.branch else None,
            "name": self.name,
            "status": self.status.value if isinstance(self.status, DeliveryZoneStatus) else self.status,
            "zone_type": self.zone_type.value if isinstance(self.zone_type, DeliveryZoneType) else self.zone_type,
            "center_latitude": float(self.center_latitude) if self.center_latitude is not None else None,
            "center_longitude": float(self.center_longitude) if self.center_longitude is not None else None,
            "radius_meters": self.radius_meters,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<DeliveryZone {self.public_id} {self.name}>"
