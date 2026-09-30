from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class CartItem(db.Model, PublicIdMixin, TimestampMixin):
    """One product line within a cart.

    `unit_price_snapshot` is the branch-product price at the moment the
    item was added or last quantity-updated. It exists purely so the UI
    can show a "price changed since you added this" notice; it is never
    treated as authoritative. Every subtotal calculation (cart view,
    checkout validation, order creation) re-reads the live
    `BranchProduct.effective_price` - see app/cart/pricing.py.
    """

    __tablename__ = "cart_items"

    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey("carts.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_product_id = db.Column(
        db.Integer, db.ForeignKey("branch_products.id", ondelete="CASCADE"), nullable=False, index=True
    )

    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price_snapshot = db.Column(db.Numeric(10, 2), nullable=False)

    product = db.relationship("Product")
    branch_product = db.relationship("BranchProduct")

    __table_args__ = (
        db.UniqueConstraint("cart_id", "product_id", name="uq_cart_items_cart_product"),
        db.CheckConstraint("quantity > 0", name="ck_cart_items_quantity_positive"),
        db.CheckConstraint("unit_price_snapshot >= 0", name="ck_cart_items_unit_price_non_negative"),
    )

    @property
    def line_total_snapshot(self):
        return self.unit_price_snapshot * self.quantity

    def to_public_dict(self) -> dict:
        current_price = self.branch_product.effective_price if self.branch_product else None
        is_available = bool(self.branch_product and self.branch_product.is_available)
        is_product_active = bool(self.product and self.product.status.value == "ACTIVE")
        return {
            "id": self.public_id,
            "product": self.product.to_public_dict(include_images=True) if self.product else None,
            "branch_product_id": self.branch_product.public_id if self.branch_product else None,
            "quantity": self.quantity,
            "unit_price_snapshot": str(self.unit_price_snapshot),
            "current_unit_price": str(current_price) if current_price is not None else None,
            "price_changed": (
                current_price is not None and current_price != self.unit_price_snapshot
            ),
            "line_total": str(current_price * self.quantity) if current_price is not None else None,
            "is_available": is_available and is_product_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<CartItem {self.public_id} cart_id={self.cart_id} product_id={self.product_id} qty={self.quantity}>"
