import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class VendorAccountStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class VendorFinancialAccount(db.Model, PublicIdMixin, TimestampMixin):
    """The vendor-facing payable-balance projection (SRS 9/13) - one per
    vendor, provisioned lazily (see
    app/payments/vendor_finance_service.py:get_or_create_vendor_account),
    mirroring RiderWallet's role for riders. `cached_payable_balance` is
    always reconcilable from this vendor's VENDOR_PAYABLE ledger account.
    """

    __tablename__ = "vendor_financial_accounts"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(
        db.Integer, db.ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    financial_account_id = db.Column(
        db.Integer, db.ForeignKey("financial_accounts.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    currency = db.Column(db.String(3), nullable=False)
    cached_payable_balance = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    status = db.Column(
        db.Enum(VendorAccountStatus, name="vendor_account_status", native_enum=False, length=20),
        nullable=False,
        default=VendorAccountStatus.ACTIVE,
    )

    vendor = db.relationship("Vendor", backref=db.backref("financial_account", uselist=False))
    financial_account = db.relationship("FinancialAccount")
    payouts = db.relationship(
        "VendorPayout", backref="vendor_account", lazy="dynamic", cascade="all, delete-orphan",
        order_by="VendorPayout.requested_at.desc()",
    )

    __table_args__ = (
        db.CheckConstraint("cached_payable_balance >= 0", name="ck_vendor_financial_accounts_balance_non_negative"),
    )

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "vendor_id": self.vendor.public_id if self.vendor else None,
            "currency": self.currency,
            "payable_balance": str(self.cached_payable_balance),
            "status": self.status.value if isinstance(self.status, VendorAccountStatus) else self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<VendorFinancialAccount vendor_id={self.vendor_id} payable={self.cached_payable_balance}>"
