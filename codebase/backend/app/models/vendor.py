import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class VendorStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DISABLED = "DISABLED"


class Vendor(db.Model, PublicIdMixin, TimestampMixin):
    __tablename__ = "vendors"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    phone = db.Column(db.String(32), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    logo_url = db.Column(db.String(500), nullable=True)

    status = db.Column(
        db.Enum(VendorStatus, name="vendor_status", native_enum=False, length=20),
        nullable=False,
        default=VendorStatus.ACTIVE,
        index=True,
    )

    # Phase 6: cached rating aggregate over this vendor's PUBLISHED reviews,
    # recomputed by app/reviews/service.py on every review status change -
    # never written to directly elsewhere, so it can never drift out of
    # sync with the underlying reviews.
    rating_average = db.Column(db.Numeric(3, 2), nullable=True)
    rating_count = db.Column(db.Integer, nullable=False, default=0)

    owner = db.relationship("User", backref=db.backref("vendor_profile", uselist=False))
    branches = db.relationship("Branch", backref="vendor", lazy="dynamic", cascade="all, delete-orphan")
    categories = db.relationship("Category", backref="vendor", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def is_active(self) -> bool:
        return self.status == VendorStatus.ACTIVE

    def to_public_dict(self, include_owner: bool = False) -> dict:
        data = {
            "id": self.public_id,
            "name": self.name,
            "description": self.description,
            "phone": self.phone,
            "email": self.email,
            "logo_url": self.logo_url,
            "status": self.status.value if isinstance(self.status, VendorStatus) else self.status,
            "rating_average": str(self.rating_average) if self.rating_average is not None else None,
            "rating_count": self.rating_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_owner:
            data["owner_id"] = self.owner.public_id if self.owner else None
        return data

    def __repr__(self):  # pragma: no cover
        return f"<Vendor {self.public_id} {self.name}>"
