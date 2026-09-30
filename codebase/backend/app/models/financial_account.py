import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class FinancialAccountType(str, enum.Enum):
    # Memo/audit leg for the customer side of a payment capture and its
    # reversal (refund). Not a real payable - see app/payments/ledger_service.py.
    CUSTOMER_CLEARING = "CUSTOMER_CLEARING"
    # Platform-held funds captured from customers but not yet distributed
    # to vendor/rider/platform-revenue via settlement.
    PLATFORM_CLEARING = "PLATFORM_CLEARING"
    # Recognized platform commission revenue.
    PLATFORM_REVENUE = "PLATFORM_REVENUE"
    # Recognized platform advertising revenue (Phase 6) - kept separate
    # from PLATFORM_REVENUE (order commission) so the admin finance
    # dashboard can report each revenue stream independently.
    PLATFORM_AD_REVENUE = "PLATFORM_AD_REVENUE"
    # Funds that have left the platform's clearing account via a paid
    # vendor payout (the mirror leg that balances a VENDOR_PAYABLE debit).
    PLATFORM_PAYOUT_SETTLEMENT = "PLATFORM_PAYOUT_SETTLEMENT"
    # One per vendor: what the platform currently owes that vendor.
    VENDOR_PAYABLE = "VENDOR_PAYABLE"
    # One per rider: what the platform currently owes that rider. This is
    # the ledger-side twin of `rider_wallets` (SRS 13 models them as two
    # separate tables - this is the append-only source of truth, the wallet
    # is the rider-facing cached projection of it).
    RIDER_PAYABLE = "RIDER_PAYABLE"


class FinancialAccountOwnerType(str, enum.Enum):
    PLATFORM = "PLATFORM"
    CUSTOMER = "CUSTOMER"
    VENDOR = "VENDOR"
    RIDER = "RIDER"


class FinancialAccountStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class FinancialAccount(db.Model, PublicIdMixin, TimestampMixin):
    """A ledger account in the double-entry model (SRS 11/13). PLATFORM-
    owned accounts (CLEARING/REVENUE/PAYOUT_SETTLEMENT) are singletons
    (owner_id NULL); CUSTOMER/VENDOR/RIDER accounts are one per owner,
    provisioned lazily on first use - see
    app/payments/ledger_service.py:get_or_create_account.
    """

    __tablename__ = "financial_accounts"

    id = db.Column(db.Integer, primary_key=True)
    account_type = db.Column(
        db.Enum(FinancialAccountType, name="financial_account_type", native_enum=False, length=30),
        nullable=False,
        index=True,
    )
    owner_type = db.Column(
        db.Enum(FinancialAccountOwnerType, name="financial_account_owner_type", native_enum=False, length=20),
        nullable=False,
        index=True,
    )
    # NULL for platform singleton accounts; a users.id for CUSTOMER/RIDER-
    # owned accounts (riders/customers are users); a vendors.id for
    # VENDOR-owned accounts. Deliberately not a hard FK (the owning table
    # differs by owner_type) - resolved defensively in ledger_service.
    owner_id = db.Column(db.Integer, nullable=True, index=True)
    currency = db.Column(db.String(3), nullable=False)
    status = db.Column(
        db.Enum(FinancialAccountStatus, name="financial_account_status", native_enum=False, length=20),
        nullable=False,
        default=FinancialAccountStatus.ACTIVE,
    )

    ledger_entries = db.relationship("LedgerEntry", backref="account", lazy="dynamic")

    __table_args__ = (
        db.UniqueConstraint(
            "account_type", "owner_type", "owner_id", "currency", name="uq_financial_accounts_identity"
        ),
        db.Index("ix_financial_accounts_type_owner", "account_type", "owner_id"),
    )

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "account_type": self.account_type.value if isinstance(self.account_type, FinancialAccountType) else self.account_type,
            "owner_type": self.owner_type.value if isinstance(self.owner_type, FinancialAccountOwnerType) else self.owner_type,
            "currency": self.currency,
            "status": self.status.value if isinstance(self.status, FinancialAccountStatus) else self.status,
        }

    def __repr__(self):  # pragma: no cover
        return f"<FinancialAccount {self.account_type} owner={self.owner_type}:{self.owner_id}>"
