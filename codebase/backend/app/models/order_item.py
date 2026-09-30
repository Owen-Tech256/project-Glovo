from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class OrderItem(db.Model, PublicIdMixin, TimestampMixin):
    """An immutable line item captured at order-creation time.

    `product_id` is kept for internal joins/reporting only - every field the
    API returns comes from the snapshot columns, never a live join to
    `products`, so an order always displays exactly what the customer
    bought even if the product is later renamed, repriced or archived.
    """

    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)

    product_name_snapshot = db.Column(db.String(200), nullable=False)
    sku_snapshot = db.Column(db.String(64), nullable=True)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    line_total = db.Column(db.Numeric(10, 2), nullable=False)

    __table_args__ = (
        db.CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        db.CheckConstraint("unit_price >= 0", name="ck_order_items_unit_price_non_negative"),
        db.CheckConstraint("line_total >= 0", name="ck_order_items_line_total_non_negative"),
    )

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "product_name": self.product_name_snapshot,
            "sku": self.sku_snapshot,
            "unit_price": str(self.unit_price),
            "quantity": self.quantity,
            "line_total": str(self.line_total),
        }

    def __repr__(self):  # pragma: no cover
        return f"<OrderItem {self.public_id} order_id={self.order_id} {self.product_name_snapshot} x{self.quantity}>"
