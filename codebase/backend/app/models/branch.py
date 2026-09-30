import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class BranchStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CLOSED = "CLOSED"


class Branch(db.Model, PublicIdMixin, TimestampMixin):
    __tablename__ = "branches"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)

    name = db.Column(db.String(150), nullable=False)
    address = db.Column(db.String(500), nullable=False)
    latitude = db.Column(db.Numeric(9, 6), nullable=False)
    longitude = db.Column(db.Numeric(9, 6), nullable=False)
    phone = db.Column(db.String(32), nullable=True)

    status = db.Column(
        db.Enum(BranchStatus, name="branch_status", native_enum=False, length=20),
        nullable=False,
        default=BranchStatus.ACTIVE,
        index=True,
    )

    delivery_zones = db.relationship(
        "DeliveryZone", backref="branch", lazy="dynamic", cascade="all, delete-orphan"
    )
    branch_products = db.relationship(
        "BranchProduct", backref="branch", lazy="dynamic", cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_branches_latitude_range"),
        db.CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_branches_longitude_range"),
        db.Index("ix_branches_vendor_status", "vendor_id", "status"),
    )

    @property
    def is_active(self) -> bool:
        return self.status == BranchStatus.ACTIVE

    def is_served_at(self, latitude: float, longitude: float) -> bool:
        """True if any active delivery zone on this branch covers the point."""
        return any(
            zone.covers(latitude, longitude)
            for zone in self.delivery_zones
            if zone.is_active
        )

    def to_public_dict(self, distance_meters: float | None = None) -> dict:
        data = {
            "id": self.public_id,
            "vendor_id": self.vendor.public_id if self.vendor else None,
            "vendor_name": self.vendor.name if self.vendor else None,
            "vendor_rating_average": (
                float(self.vendor.rating_average) if self.vendor and self.vendor.rating_average is not None else None
            ),
            "vendor_rating_count": self.vendor.rating_count if self.vendor else 0,
            "name": self.name,
            "address": self.address,
            "latitude": float(self.latitude) if self.latitude is not None else None,
            "longitude": float(self.longitude) if self.longitude is not None else None,
            "phone": self.phone,
            "status": self.status.value if isinstance(self.status, BranchStatus) else self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if distance_meters is not None:
            data["distance_meters"] = round(distance_meters)
        return data

    def __repr__(self):  # pragma: no cover
        return f"<Branch {self.public_id} {self.name}>"
