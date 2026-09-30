import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class OrderStatus(str, enum.Enum):
    CREATED = "CREATED"
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PAYMENT_CONFIRMED = "PAYMENT_CONFIRMED"
    VENDOR_ACCEPTED = "VENDOR_ACCEPTED"
    PREPARING = "PREPARING"
    READY = "READY"
    CANCELLED = "CANCELLED"
    # Phase 4 (logistics): the reserved extension anticipated by the Phase 3
    # comment above. Transition rules live in app/orders/state_machine.py;
    # every step past READY is driven by the logistics layer
    # (app/logistics/), never set directly.
    RIDER_ASSIGNED = "RIDER_ASSIGNED"
    PICKED_UP = "PICKED_UP"
    DELIVERING = "DELIVERING"
    DELIVERED = "DELIVERED"


class Order(db.Model, PublicIdMixin, TimestampMixin):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    public_order_number = db.Column(db.String(32), unique=True, nullable=False, index=True)

    customer_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False, index=True)
    source_cart_id = db.Column(db.Integer, db.ForeignKey("carts.id", ondelete="SET NULL"), nullable=True, index=True)

    status = db.Column(
        db.Enum(OrderStatus, name="order_status", native_enum=False, length=20),
        nullable=False,
        default=OrderStatus.CREATED,
        index=True,
    )

    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    fees = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    # Phase 6: the promotion discount applied at order creation, already
    # subtracted out of `total` below (total = subtotal - discount_total +
    # fees). Kept as its own column - rather than only living on
    # OrderPromotion - so every money read of an order (payment amount,
    # commission basis, admin/customer order views) can see it without an
    # extra join; app/models/order_promotion.py holds the full snapshot of
    # *which* promotion produced it.
    discount_total = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(10, 2), nullable=False)

    # Client-supplied, optional. Scoped per-customer (not globally unique) so
    # two different customers can't collide on a client-generated key.
    idempotency_key = db.Column(db.String(128), nullable=True)

    cancelled_at = db.Column(db.DateTime(timezone=True), nullable=True)
    cancellation_reason = db.Column(db.String(500), nullable=True)

    customer = db.relationship("User", backref=db.backref("orders", lazy="dynamic"))
    branch = db.relationship("Branch", backref=db.backref("orders", lazy="dynamic"))
    source_cart = db.relationship("Cart", backref=db.backref("orders", lazy="dynamic"))

    items = db.relationship(
        "OrderItem", backref="order", lazy="dynamic", cascade="all, delete-orphan", order_by="OrderItem.id"
    )
    status_history = db.relationship(
        "OrderStatusHistory", backref="order", lazy="dynamic", cascade="all, delete-orphan",
        order_by="OrderStatusHistory.created_at",
    )
    address_snapshot = db.relationship(
        "OrderAddressSnapshot", backref="order", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.CheckConstraint("subtotal >= 0", name="ck_orders_subtotal_non_negative"),
        db.CheckConstraint("fees >= 0", name="ck_orders_fees_non_negative"),
        db.CheckConstraint("discount_total >= 0", name="ck_orders_discount_total_non_negative"),
        db.CheckConstraint("total >= 0", name="ck_orders_total_non_negative"),
        db.UniqueConstraint("customer_id", "idempotency_key", name="uq_orders_customer_idempotency_key"),
        db.Index("ix_orders_branch_status", "branch_id", "status"),
        db.Index("ix_orders_customer_status", "customer_id", "status"),
    )

    def to_public_dict(self, include_items: bool = True, include_address: bool = True) -> dict:
        data = {
            "id": self.public_id,
            "order_number": self.public_order_number,
            "customer_id": self.customer.public_id if self.customer else None,
            "branch_id": self.branch.public_id if self.branch else None,
            "branch_name": self.branch.name if self.branch else None,
            "vendor_name": self.branch.vendor.name if self.branch and self.branch.vendor else None,
            "status": self.status.value if isinstance(self.status, OrderStatus) else self.status,
            "subtotal": str(self.subtotal),
            "fees": str(self.fees),
            "discount_total": str(self.discount_total),
            "total": str(self.total),
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "cancellation_reason": self.cancellation_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_items:
            data["items"] = [item.to_public_dict() for item in self.items]
        if include_address and self.address_snapshot:
            data["delivery_address"] = self.address_snapshot.to_public_dict()
        if self.applied_promotion is not None:
            data["applied_promotion"] = self.applied_promotion.to_public_dict()
        return data

    def __repr__(self):  # pragma: no cover
        return f"<Order {self.public_order_number} status={self.status}>"
