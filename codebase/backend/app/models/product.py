import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class ProductStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class Product(db.Model, PublicIdMixin, TimestampMixin):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True)

    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    sku = db.Column(db.String(64), nullable=True, index=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)

    status = db.Column(
        db.Enum(ProductStatus, name="product_status", native_enum=False, length=20),
        nullable=False,
        default=ProductStatus.ACTIVE,
        index=True,
    )

    # Phase 6: cached rating aggregate over this product's PUBLISHED
    # reviews - see the matching column on app/models/vendor.py for the
    # recompute contract. Product reviews are an optional, admin-toggleable
    # feature (PRODUCT_REVIEWS_ENABLED) - see app/reviews/service.py.
    rating_average = db.Column(db.Numeric(3, 2), nullable=True)
    rating_count = db.Column(db.Integer, nullable=False, default=0)

    images = db.relationship(
        "ProductImage", backref="product", lazy="dynamic",
        cascade="all, delete-orphan", order_by="ProductImage.sort_order",
    )
    branch_links = db.relationship(
        "BranchProduct", backref="product", lazy="dynamic", cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.CheckConstraint("price >= 0", name="ck_products_price_non_negative"),
        db.Index("ix_products_category_status", "category_id", "status"),
    )

    @property
    def vendor(self):
        return self.category.vendor if self.category else None

    def to_public_dict(self, include_images: bool = True) -> dict:
        data = {
            "id": self.public_id,
            "category_id": self.category.public_id if self.category else None,
            "name": self.name,
            "description": self.description,
            "sku": self.sku,
            "price": str(self.price) if self.price is not None else None,
            "status": self.status.value if isinstance(self.status, ProductStatus) else self.status,
            "rating_average": str(self.rating_average) if self.rating_average is not None else None,
            "rating_count": self.rating_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_images:
            data["images"] = [img.to_public_dict() for img in self.images]
        return data

    def __repr__(self):  # pragma: no cover
        return f"<Product {self.public_id} {self.name}>"
