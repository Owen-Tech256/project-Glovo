from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class ProductImage(db.Model, PublicIdMixin, TimestampMixin):
    __tablename__ = "product_images"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)

    image_url = db.Column(db.String(500), nullable=False)
    alt_text = db.Column(db.String(255), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "product_id": self.product.public_id if self.product else None,
            "image_url": self.image_url,
            "alt_text": self.alt_text,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<ProductImage {self.public_id} product_id={self.product_id}>"
