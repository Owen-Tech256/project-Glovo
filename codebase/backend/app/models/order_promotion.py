"""
Immutable per-order snapshot of whichever promotion discounted it (SRS 4:
"store enough historical data... so financial reporting later is not
affected by promotion edits/deletions"). Written once, inside the same
atomic transaction as order creation, and never updated afterwards -
editing or deleting the underlying Promotion later must not change what
an already-placed order shows or how it was paid/settled.
"""
from app.extensions import db
from app.models.base import TimestampMixin


class OrderPromotion(db.Model, TimestampMixin):
    __tablename__ = "order_promotions"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    # SET NULL (not CASCADE): deleting a promotion later must never remove
    # or corrupt a historical order's snapshot - only the live FK link is
    # cleared, all snapshot fields below remain intact.
    promotion_id = db.Column(db.Integer, db.ForeignKey("promotions.id", ondelete="SET NULL"), nullable=True, index=True)

    code_snapshot = db.Column(db.String(40), nullable=True)
    name_snapshot = db.Column(db.String(150), nullable=False)
    type_snapshot = db.Column(db.String(20), nullable=False)
    value_snapshot = db.Column(db.Numeric(10, 2), nullable=False)
    discount_amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False)

    order = db.relationship("Order", backref=db.backref("applied_promotion", uselist=False, cascade="all, delete-orphan"))
    promotion = db.relationship("Promotion")

    __table_args__ = (
        db.CheckConstraint("discount_amount >= 0", name="ck_order_promotions_discount_non_negative"),
    )

    def to_public_dict(self) -> dict:
        return {
            "code": self.code_snapshot,
            "name": self.name_snapshot,
            "type": self.type_snapshot,
            "value": str(self.value_snapshot),
            "discount_amount": str(self.discount_amount),
            "currency": self.currency,
        }

    def __repr__(self):  # pragma: no cover
        return f"<OrderPromotion order_id={self.order_id} discount={self.discount_amount}>"
