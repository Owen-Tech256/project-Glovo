import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class VendorPayoutStatus(str, enum.Enum):
    REQUESTED = "REQUESTED"
    PROCESSING = "PROCESSING"
    PAID = "PAID"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class VendorPayout(db.Model, PublicIdMixin, TimestampMixin):
    """One vendor payout request/attempt (SRS 9). The ledger-affecting
    DEBIT against the vendor's VENDOR_PAYABLE account is posted only once,
    at the instant this row first reaches PAID (see
    app/payments/vendor_finance_service.py) - REQUESTED/PROCESSING/FAILED
    never touch the ledger, which is what makes a FAILED payout safe to
    retry without ever double-spending the vendor's payable balance
    (implementation prompt 7: "Prevent double spending of payable funds").
    """

    __tablename__ = "vendor_payouts"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False, index=True)
    vendor_account_id = db.Column(
        db.Integer, db.ForeignKey("vendor_financial_accounts.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    status = db.Column(
        db.Enum(VendorPayoutStatus, name="vendor_payout_status", native_enum=False, length=20),
        nullable=False,
        default=VendorPayoutStatus.REQUESTED,
        index=True,
    )
    # Where the payout is sent - a plain descriptor/reference string only
    # (e.g. a masked bank account label). Never a raw account/card number
    # (SRS 6: "Do not store raw card numbers, CVV or equivalent sensitive
    # credentials" - the same rule applied here to payout destinations).
    destination_reference = db.Column(db.String(255), nullable=False)
    provider_reference = db.Column(db.String(255), nullable=True, index=True)
    failure_reason = db.Column(db.String(500), nullable=True)

    idempotency_key = db.Column(db.String(128), nullable=True)

    requested_at = db.Column(db.DateTime(timezone=True), nullable=False)
    processed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    vendor = db.relationship("Vendor")

    __table_args__ = (
        db.CheckConstraint("amount > 0", name="ck_vendor_payouts_amount_positive"),
        db.UniqueConstraint("vendor_id", "idempotency_key", name="uq_vendor_payouts_vendor_idempotency_key"),
        db.Index("ix_vendor_payouts_vendor_status", "vendor_id", "status"),
    )

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "vendor_id": self.vendor.public_id if self.vendor else None,
            "amount": str(self.amount),
            "currency": self.currency,
            "status": self.status.value if isinstance(self.status, VendorPayoutStatus) else self.status,
            "destination_reference": self.destination_reference,
            "provider_reference": self.provider_reference,
            "failure_reason": self.failure_reason,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<VendorPayout {self.public_id} vendor_id={self.vendor_id} {self.status} {self.amount}>"
