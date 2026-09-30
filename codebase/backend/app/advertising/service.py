"""
Ad campaign lifecycle + billable event ingestion (SRS 5).

Budget enforcement mirrors the vendor payout double-spend protection in
app/payments/vendor_finance_service.py: `record_event` row-locks the
AdCampaign before checking/spending its budget, so two concurrent tracking
beacons for the same campaign can never both slip in under the budget cap.
Idempotency (SRS 5: "prevent fraudulent or duplicate ad interaction
counts") is a pre-check on `event_reference` before that lock is taken,
with a race fallback on the unique constraint - the same two-layer shape
app/orders/service.py's idempotency check uses.
"""
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.common.errors import NotFoundError, ValidationAppError, AuthorizationError
from app.models.ad_campaign import (
    AdCampaign, AdObjective, AdTargetType, AdPricingModel, AdCampaignStatus, BILLABLE_STATUSES,
)
from app.models.ad_event import AdEvent, AdEventType
from app.models.financial_account import FinancialAccountType, FinancialAccountOwnerType
from app.models.financial_transaction import FinancialTransactionType, FinancialReferenceType
from app.models.ledger_entry import LedgerEntryType
from app.payments import ledger_service
from app.payments.ledger_service import LedgerLeg
from app.payments import vendor_finance_service

FOUR_PLACES = Decimal("0.0001")


def _resolve_target(vendor, target_type: AdTargetType, target_public_id: str | None) -> int:
    """Resolves a client-facing target public_id to the internal integer
    id AdCampaign.target_id stores, verifying it belongs to `vendor` -
    same public_id-resolution + ownership-check shape as
    app/promotions/service.py:resolve_scope_target_ids."""
    if target_type == AdTargetType.VENDOR:
        return vendor.id
    if not target_public_id:
        raise ValidationAppError("target_id is required for this target_type.", code="AD_TARGET_REQUIRED")

    if target_type == AdTargetType.BRANCH:
        from app.models.branch import Branch

        row = Branch.query.filter_by(public_id=target_public_id).first()
        owner_id = row.vendor_id if row else None
    elif target_type == AdTargetType.CATEGORY:
        from app.models.category import Category

        row = Category.query.filter_by(public_id=target_public_id).first()
        owner_id = row.vendor_id if row else None
    else:  # PRODUCT
        from app.models.product import Product

        row = Product.query.filter_by(public_id=target_public_id).first()
        owner_id = row.category.vendor_id if row and row.category else None

    if row is None:
        raise NotFoundError("Ad target not found.")
    if owner_id != vendor.id:
        raise AuthorizationError("An ad campaign can only target your own catalog.")
    return row.id


def create_campaign(vendor, data: dict, requires_approval: bool) -> AdCampaign:
    target_type = AdTargetType(data["target_type"])
    target_id = _resolve_target(vendor, target_type, data.get("target_id"))

    campaign = AdCampaign(
        vendor_id=vendor.id,
        name=data["name"],
        objective=AdObjective(data.get("objective", AdObjective.SPONSORED_LISTING.value)),
        target_type=target_type,
        target_id=target_id,
        pricing_model=AdPricingModel(data.get("pricing_model", AdPricingModel.CPC.value)),
        bid_amount=data["bid_amount"],
        daily_budget=data.get("daily_budget"),
        total_budget=data["total_budget"],
        status=AdCampaignStatus.PENDING_REVIEW if requires_approval else AdCampaignStatus.ACTIVE,
        starts_at=data.get("starts_at"),
        ends_at=data.get("ends_at"),
    )
    db.session.add(campaign)
    db.session.commit()
    return campaign


def update_campaign(campaign: AdCampaign, data: dict) -> AdCampaign:
    if campaign.status in (AdCampaignStatus.REJECTED, AdCampaignStatus.CANCELLED, AdCampaignStatus.COMPLETED):
        raise ValidationAppError("This campaign can no longer be edited.", code="AD_CAMPAIGN_NOT_EDITABLE")
    for field in ("name", "bid_amount", "daily_budget", "total_budget", "starts_at", "ends_at"):
        if field in data:
            setattr(campaign, field, data[field])
    db.session.commit()
    return campaign


def pause_campaign(campaign: AdCampaign) -> AdCampaign:
    if campaign.status != AdCampaignStatus.ACTIVE:
        raise ValidationAppError("Only an active campaign can be paused.", code="AD_CAMPAIGN_NOT_ACTIVE")
    campaign.status = AdCampaignStatus.PAUSED
    db.session.commit()
    return campaign


def resume_campaign(campaign: AdCampaign) -> AdCampaign:
    if campaign.status != AdCampaignStatus.PAUSED:
        raise ValidationAppError("Only a paused campaign can be resumed.", code="AD_CAMPAIGN_NOT_PAUSED")
    if campaign.remaining_budget <= 0:
        raise ValidationAppError("This campaign has exhausted its budget.", code="AD_CAMPAIGN_BUDGET_EXHAUSTED")
    campaign.status = AdCampaignStatus.ACTIVE
    db.session.commit()
    return campaign


def cancel_campaign(campaign: AdCampaign) -> AdCampaign:
    if campaign.status in (AdCampaignStatus.CANCELLED, AdCampaignStatus.COMPLETED):
        raise ValidationAppError("This campaign is already finished.", code="AD_CAMPAIGN_NOT_CANCELLABLE")
    campaign.status = AdCampaignStatus.CANCELLED
    db.session.commit()
    return campaign


# --- Admin moderation ----------------------------------------------------

def admin_approve_campaign(campaign: AdCampaign, admin_user) -> AdCampaign:
    if campaign.status != AdCampaignStatus.PENDING_REVIEW:
        raise ValidationAppError("Only a pending campaign can be approved.", code="AD_CAMPAIGN_NOT_PENDING")
    campaign.status = AdCampaignStatus.ACTIVE
    campaign.reviewed_by_user_id = admin_user.id
    campaign.reviewed_at = ledger_service.utcnow()
    db.session.commit()

    from app.notifications.events import notify
    from app.models.notification import NotificationCategory

    notify(
        campaign.vendor.owner, NotificationCategory.ADVERTISING, template_key="ad_campaign_approved",
        context={"campaign_name": campaign.name}, entity_type="AD_CAMPAIGN", entity_id=campaign.public_id,
    )
    return campaign


def admin_reject_campaign(campaign: AdCampaign, admin_user, reason: str) -> AdCampaign:
    if campaign.status != AdCampaignStatus.PENDING_REVIEW:
        raise ValidationAppError("Only a pending campaign can be rejected.", code="AD_CAMPAIGN_NOT_PENDING")
    campaign.status = AdCampaignStatus.REJECTED
    campaign.rejection_reason = reason
    campaign.reviewed_by_user_id = admin_user.id
    campaign.reviewed_at = ledger_service.utcnow()
    db.session.commit()

    from app.notifications.events import notify
    from app.models.notification import NotificationCategory

    notify(
        campaign.vendor.owner, NotificationCategory.ADVERTISING, template_key="ad_campaign_rejected",
        context={"campaign_name": campaign.name, "reason": reason}, entity_type="AD_CAMPAIGN", entity_id=campaign.public_id,
    )
    return campaign


def admin_pause_campaign(campaign: AdCampaign) -> AdCampaign:
    """Admin moderation override - unlike the vendor-facing pause_campaign,
    this works from ACTIVE or PENDING_REVIEW (SRS 5: "moderate ad content
    before/while it is live")."""
    if campaign.status not in (AdCampaignStatus.ACTIVE, AdCampaignStatus.PENDING_REVIEW):
        raise ValidationAppError("This campaign cannot be paused.", code="AD_CAMPAIGN_NOT_PAUSABLE")
    campaign.status = AdCampaignStatus.PAUSED
    db.session.commit()
    return campaign


# --- Billable event ingestion --------------------------------------------

def record_event(campaign_public_id: str, event_type: AdEventType, viewer_user, event_reference: str | None) -> AdEvent:
    if event_reference:
        existing = (
            AdEvent.query.join(AdCampaign)
            .filter(AdCampaign.public_id == campaign_public_id, AdEvent.event_reference == event_reference)
            .first()
        )
        if existing is not None:
            return existing

    campaign = AdCampaign.query.filter_by(public_id=campaign_public_id).with_for_update().first()
    if campaign is None:
        raise NotFoundError("Ad campaign not found.")
    if campaign.status not in BILLABLE_STATUSES:
        raise ValidationAppError("This campaign is not currently serving ads.", code="AD_CAMPAIGN_NOT_ACTIVE")

    is_billable_event = (
        (campaign.pricing_model == AdPricingModel.CPC and event_type == AdEventType.CLICK)
        or (campaign.pricing_model == AdPricingModel.CPM and event_type == AdEventType.IMPRESSION)
    )
    billed_amount = Decimal("0")
    vendor_account = None
    if is_billable_event and campaign.remaining_budget > 0:
        # Ad spend is capped at whichever is smaller: the campaign's own
        # remaining budget, or the vendor's currently available payable
        # balance - a vendor can never be billed into debt for ads
        # (VendorFinancialAccount.cached_payable_balance has a >= 0 check
        # constraint, the same invariant app/payments/refund_service.py's
        # module docstring cites for why refunds never claw back
        # settlements). A vendor who has spent up to their balance simply
        # stops accruing further ad charges until more balance comes in
        # from settlement - the campaign itself stays ACTIVE rather than
        # moving to BUDGET_EXHAUSTED, since it's the vendor's balance, not
        # the campaign's budget, that is the binding constraint here.
        vendor_account = vendor_finance_service.get_or_create_vendor_account(campaign.vendor)
        unit_cost = campaign.bid_amount / Decimal("1000") if campaign.pricing_model == AdPricingModel.CPM else campaign.bid_amount
        spendable = min(campaign.remaining_budget, vendor_account.cached_payable_balance)
        if spendable > 0:
            billed_amount = min(unit_cost, spendable).quantize(FOUR_PLACES, rounding=ROUND_HALF_UP)

    event = AdEvent(
        campaign_id=campaign.id,
        event_type=event_type,
        viewer_user_id=viewer_user.id if viewer_user else None,
        event_reference=event_reference,
        billed_amount=billed_amount,
        occurred_at=ledger_service.utcnow(),
    )
    db.session.add(event)

    if billed_amount > 0:
        campaign.spent_total = campaign.spent_total + billed_amount
        vendor_ledger_account = ledger_service.get_or_create_account(
            FinancialAccountType.VENDOR_PAYABLE, FinancialAccountOwnerType.VENDOR, owner_id=campaign.vendor_id
        )
        ad_revenue_account = ledger_service.get_or_create_account(
            FinancialAccountType.PLATFORM_AD_REVENUE, FinancialAccountOwnerType.PLATFORM
        )
        legs = [
            LedgerLeg(vendor_ledger_account, LedgerEntryType.DEBIT, billed_amount, description=f"Ad spend: campaign {campaign.public_id}"),
            LedgerLeg(ad_revenue_account, LedgerEntryType.CREDIT, billed_amount, description=f"Ad spend: campaign {campaign.public_id}"),
        ]
        db.session.flush()  # obtain event.id for a deterministic idempotency key
        _txn, created = ledger_service.post_transaction(
            FinancialTransactionType.AD_SPEND, FinancialReferenceType.AD_CAMPAIGN, campaign.id, legs,
            idempotency_key=f"ad_event:{event.id}",
            description=f"Ad spend for campaign {campaign.name}.",
        )
        if created:
            vendor_finance_service.debit_payable(vendor_account, billed_amount)

        if campaign.spent_total >= campaign.total_budget:
            campaign.status = AdCampaignStatus.BUDGET_EXHAUSTED

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing = (
            AdEvent.query.join(AdCampaign)
            .filter(AdCampaign.public_id == campaign_public_id, AdEvent.event_reference == event_reference)
            .first()
        )
        if existing is not None:
            return existing
        raise
    return event


# --- Lookups -------------------------------------------------------------

def get_vendor_owned_campaign_or_404(vendor, campaign_public_id: str) -> AdCampaign:
    campaign = AdCampaign.query.filter_by(public_id=campaign_public_id, vendor_id=vendor.id).first()
    if campaign is None:
        raise NotFoundError("Ad campaign not found.")
    return campaign


def get_any_campaign_or_404(campaign_public_id: str) -> AdCampaign:
    campaign = AdCampaign.query.filter_by(public_id=campaign_public_id).first()
    if campaign is None:
        raise NotFoundError("Ad campaign not found.")
    return campaign


def list_vendor_campaigns(vendor, status: str | None = None):
    query = AdCampaign.query.filter_by(vendor_id=vendor.id)
    if status:
        query = query.filter(AdCampaign.status == status)
    return query.order_by(AdCampaign.created_at.desc()).all()


def list_all_campaigns(status: str | None = None, page: int = 1, per_page: int = 20):
    query = AdCampaign.query
    if status:
        query = query.filter(AdCampaign.status == status)
    return query.order_by(AdCampaign.created_at.desc()).paginate(
        page=max(page, 1), per_page=max(min(per_page, 100), 1), error_out=False
    )


def campaign_performance(campaign: AdCampaign) -> dict:
    impressions = campaign.events.filter_by(event_type=AdEventType.IMPRESSION).count()
    clicks = campaign.events.filter_by(event_type=AdEventType.CLICK).count()
    return {
        "impressions": impressions,
        "clicks": clicks,
        "click_through_rate": str(round(clicks / impressions, 4)) if impressions else "0",
        "spent_total": str(campaign.spent_total),
        "remaining_budget": str(campaign.remaining_budget),
    }
