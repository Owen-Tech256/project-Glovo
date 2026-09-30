import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class CartStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CONVERTED = "CONVERTED"
    ABANDONED = "ABANDONED"


class Cart(db.Model, PublicIdMixin, TimestampMixin):
    """A customer's in-progress selection at a single branch.

    A cart is always scoped to exactly one branch, which is what makes
    "no mixing products from different branches" structural rather than a
    rule that has to be checked on every write: a customer who wants items
    from a second branch gets (or creates) that branch's own ACTIVE cart.

    "One active cart per customer per branch" (SRS 6.1) is enforced in the
    service layer (get-or-create-on-write) rather than a DB constraint,
    because it is a status-conditional uniqueness rule (unique only while
    status = ACTIVE) that portable unique constraints across
    Postgres/SQLite can't express cleanly - the same pragmatic choice the
    Phase 2 codebase already makes for `customer_addresses.is_default`.
    """

    __tablename__ = "carts"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True)

    status = db.Column(
        db.Enum(CartStatus, name="cart_status", native_enum=False, length=20),
        nullable=False,
        default=CartStatus.ACTIVE,
        index=True,
    )
    # Phase 6: the promotion the customer wants applied at checkout, if
    # any. Deliberately just an FK, not a stored discount amount - the
    # discount is always recomputed fresh from live promotion rules +
    # live cart contents (app/promotions/service.py:price_cart_with_promotion),
    # the same "never trust a stored total" stance app/cart/pricing.py
    # already takes for cart pricing generally. SET NULL on delete so a
    # promotion admin deletion can never leave a cart pointing at nothing.
    applied_promotion_id = db.Column(
        db.Integer, db.ForeignKey("promotions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    customer = db.relationship("User", backref=db.backref("carts", lazy="dynamic", cascade="all, delete-orphan"))
    branch = db.relationship("Branch", backref=db.backref("carts", lazy="dynamic", cascade="all, delete-orphan"))
    applied_promotion = db.relationship("Promotion")
    items = db.relationship(
        "CartItem", backref="cart", lazy="dynamic", cascade="all, delete-orphan",
        order_by="CartItem.created_at",
    )

    __table_args__ = (
        db.Index("ix_carts_customer_branch_status", "customer_id", "branch_id", "status"),
    )

    @property
    def is_active(self) -> bool:
        return self.status == CartStatus.ACTIVE

    def to_public_dict(self, include_pricing: bool = True) -> dict:
        items = self.items.all() if hasattr(self.items, "all") else list(self.items)
        data = {
            "id": self.public_id,
            "branch_id": self.branch.public_id if self.branch else None,
            "branch_name": self.branch.name if self.branch else None,
            "status": self.status.value if isinstance(self.status, CartStatus) else self.status,
            "items": [item.to_public_dict() for item in items],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_pricing:
            from app.cart.pricing import price_cart

            priced = price_cart(self)
            data["subtotal"] = str(priced.subtotal)
            data["item_count"] = priced.item_count
            data["has_issues"] = bool(priced.issues)
            data["issues"] = priced.issues

            from app.promotions.service import price_cart_with_promotion

            discount, promotion, promo_issue = price_cart_with_promotion(self, priced)
            data["discount_total"] = str(discount)
            data["total"] = str(priced.subtotal - discount)
            data["applied_promotion"] = promotion.to_public_dict() if promotion else None
            data["promotion_issue"] = promo_issue
        return data

    def __repr__(self):  # pragma: no cover
        return f"<Cart {self.public_id} customer_id={self.customer_id} branch_id={self.branch_id} {self.status}>"
