import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class RefundStatus(str, enum.Enum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PROCESSING = "PROCESSING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class Refund(db.Model, PublicIdMixin, TimestampMixin):
    """One full or partial refund against a Payment (SRS 10). Multiple
    Refund rows may exist per payment (several partial refunds); the sum of
    every SUCCEEDED refund's `amount` for a payment can never exceed that
    payment's own `amount` - enforced, under a row lock, in
    app/payments/refund_service.py rather than a DB constraint (the
    constraint would need to aggregate sibling rows, which CHECK
    constraints can't do portably).
    """

    __tablename__ = "refunds"

    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False, index=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True)

    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    reason = db.Column(db.String(500), nullable=False)
    status = db.Column(
        db.Enum(RefundStatus, name="refund_status", native_enum=False, length=20),
        nullable=False,
        default=RefundStatus.REQUESTED,
        index=True,
    )

    requested_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    provider_reference = db.Column(db.String(255), nullable=True, index=True)
    failure_reason = db.Column(db.String(500), nullable=True)
    idempotency_key = db.Column(db.String(128), nullable=True)

    approved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    processed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    order = db.relationship("Order", backref=db.backref("refunds", lazy="dynamic"))
    requested_by = db.relationship("User", foreign_keys=[requested_by_user_id])
    approved_by = db.relationship("User", foreign_keys=[approved_by_user_id])

    __table_args__ = (
        db.CheckConstraint("amount > 0", name="ck_refunds_amount_positive"),
        db.UniqueConstraint(
            "requested_by_user_id", "idempotency_key", name="uq_refunds_requester_idempotency_key"
        ),
        db.Index("ix_refunds_payment_status", "payment_id", "status"),
    )

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "order_id": self.order.public_id if self.order else None,
            "payment_id": self.payment.public_id if self.payment else None,
            "amount": str(self.amount),
            "currency": self.currency,
            "reason": self.reason,
            "status": self.status.value if isinstance(self.status, RefundStatus) else self.status,
            "requested_by": self.requested_by.public_id if self.requested_by else None,
            "approved_by": self.approved_by.public_id if self.approved_by else None,
            "provider_reference": self.provider_reference,
            "failure_reason": self.failure_reason,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<Refund {self.public_id} payment_id={self.payment_id} {self.status} {self.amount}>"
