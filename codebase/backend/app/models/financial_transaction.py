import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class FinancialTransactionType(str, enum.Enum):
    PAYMENT_CAPTURE = "PAYMENT_CAPTURE"
    ORDER_SETTLEMENT = "ORDER_SETTLEMENT"
    REFUND = "REFUND"
    VENDOR_PAYOUT = "VENDOR_PAYOUT"
    WALLET_ADJUSTMENT = "WALLET_ADJUSTMENT"
    # Phase 6: a vendor's advertising spend, debited from their payable
    # balance as billable ad events (impressions/clicks) accrue - see
    # app/advertising/service.py.
    AD_SPEND = "AD_SPEND"


class FinancialReferenceType(str, enum.Enum):
    PAYMENT = "PAYMENT"
    ORDER = "ORDER"
    REFUND = "REFUND"
    VENDOR_PAYOUT = "VENDOR_PAYOUT"
    WALLET_ADJUSTMENT = "WALLET_ADJUSTMENT"
    AD_CAMPAIGN = "AD_CAMPAIGN"


class FinancialTransactionStatus(str, enum.Enum):
    # A financial transaction is created POSTED, atomically, with its full
    # set of balanced ledger entries, in the same DB transaction (SRS 14:
    # "must have balanced ledger entries"; implementation prompt 5: "Make
    # financial posting atomic"). There is no separate draft/pending state
    # in this phase - a FinancialTransaction row only ever exists once its
    # ledger entries are final. REVERSED marks one that a later reversing
    # transaction has fully offset (see app/payments/refund_service.py),
    # without ever deleting or editing its original entries.
    POSTED = "POSTED"
    REVERSED = "REVERSED"


class FinancialTransaction(db.Model, PublicIdMixin, TimestampMixin):
    """One business money event (SRS 11/13): a payment capture, an order
    settlement (commission split), a refund reversal, a vendor payout, or a
    manual wallet adjustment. Always balanced - the sum of its
    ledger_entries with entry_type=DEBIT equals the sum with
    entry_type=CREDIT, enforced by app/payments/ledger_service.py before
    any entries are ever written. `reference_type`/`reference_id` point at
    whichever business object caused this transaction (mirroring the
    polymorphic pattern already used for provider_reference elsewhere in
    this codebase), so every ledger entry is traceable back to its cause.
    """

    __tablename__ = "financial_transactions"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(
        db.Enum(FinancialTransactionType, name="financial_transaction_type", native_enum=False, length=30),
        nullable=False,
        index=True,
    )
    reference_type = db.Column(
        db.Enum(FinancialReferenceType, name="financial_reference_type", native_enum=False, length=20),
        nullable=False,
        index=True,
    )
    reference_id = db.Column(db.Integer, nullable=False, index=True)
    status = db.Column(
        db.Enum(FinancialTransactionStatus, name="financial_transaction_status", native_enum=False, length=20),
        nullable=False,
        default=FinancialTransactionStatus.POSTED,
        index=True,
    )
    # Guards against double-posting the same business event twice (e.g. two
    # concurrent payment confirmations) independent of any Payment/Refund/
    # Payout-level idempotency_key - this is the ledger's own last line of
    # defense (implementation prompt 12: "Two identical payment
    # confirmations must result in one financial posting").
    idempotency_key = db.Column(db.String(150), nullable=True)
    currency = db.Column(db.String(3), nullable=False)
    description = db.Column(db.String(500), nullable=True)

    ledger_entries = db.relationship(
        "LedgerEntry", backref="financial_transaction", lazy="dynamic", cascade="all, delete-orphan",
        order_by="LedgerEntry.id",
    )

    __table_args__ = (
        db.UniqueConstraint("type", "idempotency_key", name="uq_financial_transactions_type_idempotency_key"),
        db.Index("ix_financial_transactions_reference", "reference_type", "reference_id"),
    )

    def to_public_dict(self, include_entries: bool = False) -> dict:
        data = {
            "id": self.public_id,
            "type": self.type.value if isinstance(self.type, FinancialTransactionType) else self.type,
            "reference_type": self.reference_type.value if isinstance(self.reference_type, FinancialReferenceType) else self.reference_type,
            "status": self.status.value if isinstance(self.status, FinancialTransactionStatus) else self.status,
            "currency": self.currency,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_entries:
            data["ledger_entries"] = [e.to_public_dict() for e in self.ledger_entries]
        return data

    def __repr__(self):  # pragma: no cover
        return f"<FinancialTransaction {self.public_id} {self.type} {self.status}>"
