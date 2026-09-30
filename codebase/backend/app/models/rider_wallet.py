import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class RiderWalletStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class RiderWallet(db.Model, PublicIdMixin, TimestampMixin):
    """The rider-facing wallet (SRS 8/13) - one per rider, provisioned
    lazily the same way Rider itself is (see
    app/payments/wallet_service.py:get_or_create_wallet). `financial_account_id`
    links it to the RIDER_PAYABLE ledger account that is the actual source
    of truth; `cached_available_balance`/`cached_pending_balance` are a
    performance cache only, kept in lockstep with wallet_transactions on
    every credit/debit and always re-derivable by summing this rider's
    ledger entries (SRS 5: "Balances may be cached... but must always be
    reconcilable from ledger entries").

    This phase has no external settlement delay (no real payment gateway
    imposes a clearing hold - see PHASE_5_NOTES.md), so every earning is
    credited straight to `cached_available_balance`; `cached_pending_balance`
    exists so a future phase that adds a real hold period does not need a
    schema change, but is never populated by any code path today.
    """

    __tablename__ = "rider_wallets"

    id = db.Column(db.Integer, primary_key=True)
    rider_id = db.Column(
        db.Integer, db.ForeignKey("riders.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    financial_account_id = db.Column(
        db.Integer, db.ForeignKey("financial_accounts.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    currency = db.Column(db.String(3), nullable=False)
    cached_available_balance = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    cached_pending_balance = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    status = db.Column(
        db.Enum(RiderWalletStatus, name="rider_wallet_status", native_enum=False, length=20),
        nullable=False,
        default=RiderWalletStatus.ACTIVE,
    )

    rider = db.relationship("Rider", backref=db.backref("wallet", uselist=False))
    financial_account = db.relationship("FinancialAccount")
    transactions = db.relationship(
        "WalletTransaction", backref="wallet", lazy="dynamic", cascade="all, delete-orphan",
        order_by="WalletTransaction.created_at.desc()",
    )

    __table_args__ = (
        db.CheckConstraint("cached_available_balance >= 0", name="ck_rider_wallets_available_non_negative"),
        db.CheckConstraint("cached_pending_balance >= 0", name="ck_rider_wallets_pending_non_negative"),
    )

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "rider_id": self.rider.public_id if self.rider else None,
            "currency": self.currency,
            "available_balance": str(self.cached_available_balance),
            "pending_balance": str(self.cached_pending_balance),
            "status": self.status.value if isinstance(self.status, RiderWalletStatus) else self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<RiderWallet rider_id={self.rider_id} available={self.cached_available_balance}>"
