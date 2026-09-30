from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class Category(db.Model, PublicIdMixin, TimestampMixin):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)

    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)

    products = db.relationship("Product", backref="category", lazy="dynamic", cascade="all, delete-orphan")

    __table_args__ = (
        db.Index("ix_categories_vendor_active", "vendor_id", "is_active"),
    )

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "vendor_id": self.vendor.public_id if self.vendor else None,
            "name": self.name,
            "description": self.description,
            "image_url": self.image_url,
            "sort_order": self.sort_order,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<Category {self.public_id} {self.name}>"
