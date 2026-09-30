import enum

from app.extensions import db
from app.models.base import PublicIdMixin, _utcnow


class LedgerEntryType(str, enum.Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class LedgerEntry(db.Model, PublicIdMixin):
    """One leg of a balanced FinancialTransaction (SRS 13: "append-only").
    Deliberately has no `updated_at` (unlike every other table's
    TimestampMixin) - the SRS's own data model for this table lists only
    `id, financial_transaction_id, account_id, entry_type, amount,
    currency, description, created_at; append-only`, and an editable-
    looking `updated_at` column would misrepresent what this table is.
    Every row, once written, is never updated or deleted by any code path
    in this codebase; corrections are new rows on a new reversing
    FinancialTransaction (SRS 5). It keeps PublicIdMixin like every other
    model here, so admin reconciliation views never leak internal integer
    ids over the API.
    """

    __tablename__ = "ledger_entries"

    id = db.Column(db.Integer, primary_key=True)
    financial_transaction_id = db.Column(
        db.Integer, db.ForeignKey("financial_transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id = db.Column(
        db.Integer, db.ForeignKey("financial_accounts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    entry_type = db.Column(
        db.Enum(LedgerEntryType, name="ledger_entry_type", native_enum=False, length=10), nullable=False
    )
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)

    __table_args__ = (
        db.CheckConstraint("amount > 0", name="ck_ledger_entries_amount_positive"),
        db.Index("ix_ledger_entries_account_created", "account_id", "created_at"),
    )

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "account_type": self.account.account_type.value if self.account else None,
            "entry_type": self.entry_type.value if isinstance(self.entry_type, LedgerEntryType) else self.entry_type,
            "amount": str(self.amount),
            "currency": self.currency,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<LedgerEntry account_id={self.account_id} {self.entry_type} {self.amount}>"
