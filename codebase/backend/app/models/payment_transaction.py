import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class PaymentTransactionType(str, enum.Enum):
    CHARGE = "CHARGE"
    VERIFY = "VERIFY"
    REFUND = "REFUND"


class PaymentTransactionStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class PaymentTransaction(db.Model, PublicIdMixin, TimestampMixin):
    """One provider-adapter call attempt against a Payment (SRS 13:
    "payment attempts/transactions and provider references"). A single
    Payment accumulates one row per CHARGE attempt, per server-side VERIFY
    call, and per REFUND call against it - the full attempt history a
    reconciliation review would need, independent of the Payment's own
    current (mutable) status field.
    """

    __tablename__ = "payment_transactions"

    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, index=True)

    type = db.Column(
        db.Enum(PaymentTransactionType, name="payment_transaction_type", native_enum=False, length=20),
        nullable=False,
        index=True,
    )
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    status = db.Column(
        db.Enum(PaymentTransactionStatus, name="payment_transaction_status", native_enum=False, length=20),
        nullable=False,
        index=True,
    )
    provider_reference = db.Column(db.String(255), nullable=True, index=True)
    # The provider's own event/attempt ID for this specific call, distinct
    # from payment_webhook_events.external_event_id (that table dedupes
    # inbound webhook deliveries; this field just retains whatever the
    # synchronous adapter call itself returned, for reconciliation).
    external_event_id = db.Column(db.String(255), nullable=True, index=True)
    failure_reason = db.Column(db.String(500), nullable=True)
    processed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        db.Index("ix_payment_transactions_payment_type", "payment_id", "type"),
    )

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "type": self.type.value if isinstance(self.type, PaymentTransactionType) else self.type,
            "amount": str(self.amount),
            "currency": self.currency,
            "status": self.status.value if isinstance(self.status, PaymentTransactionStatus) else self.status,
            "provider_reference": self.provider_reference,
            "failure_reason": self.failure_reason,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<PaymentTransaction payment_id={self.payment_id} {self.type} {self.status}>"
