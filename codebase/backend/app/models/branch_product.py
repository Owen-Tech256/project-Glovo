import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class BranchProductAvailability(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


class BranchProduct(db.Model, PublicIdMixin, TimestampMixin):
    """Join entity between Branch and Product. Represents whether - and at
    what price - a given product is offered at a given branch."""

    __tablename__ = "branch_products"

    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)

    price_override = db.Column(db.Numeric(10, 2), nullable=True)
    availability_status = db.Column(
        db.Enum(BranchProductAvailability, name="branch_product_availability", native_enum=False, length=20),
        nullable=False,
        default=BranchProductAvailability.AVAILABLE,
        index=True,
    )

    __table_args__ = (
        db.UniqueConstraint("branch_id", "product_id", name="uq_branch_products_branch_product"),
        db.CheckConstraint(
            "price_override IS NULL OR price_override >= 0", name="ck_branch_products_price_override_non_negative"
        ),
        db.Index("ix_branch_products_branch_availability", "branch_id", "availability_status"),
    )

    @property
    def is_available(self) -> bool:
        return self.availability_status == BranchProductAvailability.AVAILABLE

    @property
    def effective_price(self):
        if self.price_override is not None:
            return self.price_override
        return self.product.price if self.product else None

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "branch_id": self.branch.public_id if self.branch else None,
            "product": self.product.to_public_dict(include_images=True) if self.product else None,
            "price_override": str(self.price_override) if self.price_override is not None else None,
            "effective_price": str(self.effective_price) if self.effective_price is not None else None,
            "availability_status": (
                self.availability_status.value
                if isinstance(self.availability_status, BranchProductAvailability)
                else self.availability_status
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<BranchProduct branch_id={self.branch_id} product_id={self.product_id}>"
