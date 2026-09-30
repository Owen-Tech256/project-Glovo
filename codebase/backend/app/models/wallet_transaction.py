import enum

from app.extensions import db
from app.models.base import PublicIdMixin, _utcnow


class WalletTransactionType(str, enum.Enum):
    EARNING = "EARNING"
    ADJUSTMENT_CREDIT = "ADJUSTMENT_CREDIT"
    ADJUSTMENT_DEBIT = "ADJUSTMENT_DEBIT"
    PAYOUT_DEBIT = "PAYOUT_DEBIT"


class WalletTransactionStatus(str, enum.Enum):
    POSTED = "POSTED"


class WalletTransaction(db.Model, PublicIdMixin):
    """One human-readable line in a rider's wallet history (SRS 8: "Expose
    balance and transaction history to the rider"), always created in
    lockstep with - and linked to - the underlying `financial_transaction`
    that actually moved the ledger (SRS 8: "Record every wallet movement as
    a financial transaction"; "Rider wallet credits must reference the
    originating financial transaction"). No `updated_at`: like
    LedgerEntry, a posted wallet transaction is never edited.
    """

    __tablename__ = "wallet_transactions"

    id = db.Column(db.Integer, primary_key=True)
    wallet_id = db.Column(db.Integer, db.ForeignKey("rider_wallets.id", ondelete="CASCADE"), nullable=False, index=True)
    financial_transaction_id = db.Column(
        db.Integer, db.ForeignKey("financial_transactions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    type = db.Column(
        db.Enum(WalletTransactionType, name="wallet_transaction_type", native_enum=False, length=20),
        nullable=False,
        index=True,
    )
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    status = db.Column(
        db.Enum(WalletTransactionStatus, name="wallet_transaction_status", native_enum=False, length=20),
        nullable=False,
        default=WalletTransactionStatus.POSTED,
    )
    description = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)

    __table_args__ = (
        db.CheckConstraint("amount > 0", name="ck_wallet_transactions_amount_positive"),
    )

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "type": self.type.value if isinstance(self.type, WalletTransactionType) else self.type,
            "amount": str(self.amount),
            "currency": self.currency,
            "status": self.status.value if isinstance(self.status, WalletTransactionStatus) else self.status,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<WalletTransaction wallet_id={self.wallet_id} {self.type} {self.amount}>"
