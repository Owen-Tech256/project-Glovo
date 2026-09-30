"""
Vendor advertising campaigns (SRS 5). A campaign promotes one target
(a vendor's whole storefront, a branch, a product, or a category) as a
sponsored placement or banner, within a budget the platform enforces by
debiting the vendor's own payable balance as events are billed (see
app/advertising/service.py and app/payments/vendor_finance_service.py).
"""
import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class AdObjective(str, enum.Enum):
    SPONSORED_LISTING = "SPONSORED_LISTING"
    BANNER = "BANNER"


class AdTargetType(str, enum.Enum):
    VENDOR = "VENDOR"
    BRANCH = "BRANCH"
    PRODUCT = "PRODUCT"
    CATEGORY = "CATEGORY"


class AdPricingModel(str, enum.Enum):
    CPC = "CPC"  # billed per click
    CPM = "CPM"  # billed per 1,000 impressions


class AdCampaignStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# Statuses under which a campaign may still serve/bill events.
BILLABLE_STATUSES = {AdCampaignStatus.ACTIVE}


class AdCampaign(db.Model, PublicIdMixin, TimestampMixin):
    __tablename__ = "ad_campaigns"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)

    name = db.Column(db.String(150), nullable=False)
    objective = db.Column(
        db.Enum(AdObjective, name="ad_objective", native_enum=False, length=20),
        nullable=False, default=AdObjective.SPONSORED_LISTING,
    )
    target_type = db.Column(db.Enum(AdTargetType, name="ad_target_type", native_enum=False, length=20), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)

    pricing_model = db.Column(
        db.Enum(AdPricingModel, name="ad_pricing_model", native_enum=False, length=10),
        nullable=False, default=AdPricingModel.CPC,
    )
    bid_amount = db.Column(db.Numeric(10, 4), nullable=False)  # cost per billable event unit
    daily_budget = db.Column(db.Numeric(10, 2), nullable=True)
    total_budget = db.Column(db.Numeric(10, 2), nullable=False)
    spent_total = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    status = db.Column(
        db.Enum(AdCampaignStatus, name="ad_campaign_status", native_enum=False, length=20),
        nullable=False, default=AdCampaignStatus.DRAFT, index=True,
    )
    rejection_reason = db.Column(db.String(500), nullable=True)
    reviewed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    starts_at = db.Column(db.DateTime(timezone=True), nullable=True)
    ends_at = db.Column(db.DateTime(timezone=True), nullable=True)

    vendor = db.relationship("Vendor")
    events = db.relationship("AdEvent", backref="campaign", lazy="dynamic", cascade="all, delete-orphan")

    __table_args__ = (
        db.CheckConstraint("total_budget > 0", name="ck_ad_campaigns_total_budget_positive"),
        db.CheckConstraint("spent_total >= 0", name="ck_ad_campaigns_spent_non_negative"),
        db.CheckConstraint("bid_amount > 0", name="ck_ad_campaigns_bid_amount_positive"),
        db.Index("ix_ad_campaigns_vendor_status", "vendor_id", "status"),
        db.Index("ix_ad_campaigns_target", "target_type", "target_id"),
    )

    @property
    def remaining_budget(self):
        return self.total_budget - self.spent_total

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "vendor_id": self.vendor.public_id if self.vendor else None,
            "name": self.name,
            "objective": self.objective.value if isinstance(self.objective, AdObjective) else self.objective,
            "target_type": self.target_type.value if isinstance(self.target_type, AdTargetType) else self.target_type,
            "target_id": self.target_id,
            "pricing_model": self.pricing_model.value if isinstance(self.pricing_model, AdPricingModel) else self.pricing_model,
            "bid_amount": str(self.bid_amount),
            "daily_budget": str(self.daily_budget) if self.daily_budget is not None else None,
            "total_budget": str(self.total_budget),
            "spent_total": str(self.spent_total),
            "remaining_budget": str(self.remaining_budget),
            "status": self.status.value if isinstance(self.status, AdCampaignStatus) else self.status,
            "rejection_reason": self.rejection_reason,
            "starts_at": self.starts_at.isoformat() if self.starts_at else None,
            "ends_at": self.ends_at.isoformat() if self.ends_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<AdCampaign {self.public_id} {self.name} {self.status}>"
