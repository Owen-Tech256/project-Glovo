import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class PaymentStatus(str, enum.Enum):
    INITIATED = "INITIATED"
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    # Not part of the SRS's headline state list (INITIATED/PENDING/
    # SUCCEEDED/FAILED/CANCELLED) but required by SRS 6's "represent full/
    # partial refund state without destroying original payment history" -
    # a SUCCEEDED payment that has since been fully refunded needs a status
    # distinct from a live, un-refunded SUCCEEDED payment, without ever
    # mutating the original SUCCEEDED record or its succeeded_at/amount.
    # See app/payments/refund_service.py.
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"
    REFUNDED = "REFUNDED"


class Payment(db.Model, PublicIdMixin, TimestampMixin):
    """One payment attempt-and-outcome for one order. A customer may end up
    with several Payment rows for the same order (a FAILED attempt followed
    by a retry that SUCCEEDS) - `order_id` is deliberately NOT unique for
    that reason. Exactly one payment per order may ever reach SUCCEEDED;
    that invariant is enforced in app/payments/payment_service.py rather
    than a DB constraint, since "at most one of several rows has this
    status" isn't expressible as a plain unique constraint.

    `amount`/`currency` are always the server-calculated `order.total` at
    creation time (SRS 5: "never trust client-supplied... totals") - never
    client-supplied.
    """

    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)

    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    method = db.Column(db.String(32), nullable=False)
    provider = db.Column(db.String(32), nullable=False)

    status = db.Column(
        db.Enum(PaymentStatus, name="payment_status", native_enum=False, length=20),
        nullable=False,
        default=PaymentStatus.INITIATED,
        index=True,
    )

    # The provider's own identifier for this payment/charge (e.g. a gateway
    # charge ID). Retained for reconciliation (SRS 5: "Every external
    # provider reference must be retained"). Unique when present so two
    # payments can never claim the same provider-side charge.
    provider_reference = db.Column(db.String(255), nullable=True, unique=True, index=True)
    failure_reason = db.Column(db.String(500), nullable=True)

    # Client-supplied, optional, scoped per-customer (mirrors Order's own
    # idempotency_key pattern from Phase 3).
    idempotency_key = db.Column(db.String(128), nullable=True)

    succeeded_at = db.Column(db.DateTime(timezone=True), nullable=True)

    order = db.relationship("Order", backref=db.backref("payments", lazy="dynamic"))
    customer = db.relationship("User")

    transactions = db.relationship(
        "PaymentTransaction", backref="payment", lazy="dynamic", cascade="all, delete-orphan",
        order_by="PaymentTransaction.created_at",
    )
    refunds = db.relationship(
        "Refund", backref="payment", lazy="dynamic", cascade="all, delete-orphan",
        order_by="Refund.created_at",
    )

    __table_args__ = (
        db.CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        db.UniqueConstraint("customer_id", "idempotency_key", name="uq_payments_customer_idempotency_key"),
        db.Index("ix_payments_order_status", "order_id", "status"),
    )

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "order_id": self.order.public_id if self.order else None,
            "order_number": self.order.public_order_number if self.order else None,
            "amount": str(self.amount),
            "currency": self.currency,
            "method": self.method,
            "provider": self.provider,
            "status": self.status.value if isinstance(self.status, PaymentStatus) else self.status,
            "provider_reference": self.provider_reference,
            "failure_reason": self.failure_reason,
            "succeeded_at": self.succeeded_at.isoformat() if self.succeeded_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<Payment {self.public_id} order_id={self.order_id} status={self.status}>"
