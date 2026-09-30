from flask import Blueprint, request

from app.common.responses import success
from app.auth.decorators import require_role, current_user
from app.models.user import UserRole
from app.vendors.helpers import get_or_create_vendor
from app.advertising import service as ad_service
from app.advertising.schemas import AdCampaignCreateSchema, AdCampaignUpdateSchema

vendor_ads_bp = Blueprint("vendor_ads", __name__, url_prefix="/api/v1/vendor/ad-campaigns")

create_schema = AdCampaignCreateSchema()
update_schema = AdCampaignUpdateSchema()


def _requires_approval() -> bool:
    from flask import current_app

    return current_app.config.get("AD_CAMPAIGN_REQUIRES_APPROVAL", True)


@vendor_ads_bp.get("")
@require_role(UserRole.VENDOR.value)
def list_campaigns():
    vendor = get_or_create_vendor(current_user())
    status = request.args.get("status")
    campaigns = ad_service.list_vendor_campaigns(vendor, status)
    return success({"campaigns": [c.to_public_dict() for c in campaigns]})


@vendor_ads_bp.post("")
@require_role(UserRole.VENDOR.value)
def create_campaign():
    vendor = get_or_create_vendor(current_user())
    data = create_schema.load(request.get_json(silent=True) or {})
    campaign = ad_service.create_campaign(vendor, data, requires_approval=_requires_approval())
    return success({"campaign": campaign.to_public_dict()}, message="Campaign created.", status_code=201)


@vendor_ads_bp.get("/<campaign_public_id>")
@require_role(UserRole.VENDOR.value)
def get_campaign(campaign_public_id):
    vendor = get_or_create_vendor(current_user())
    campaign = ad_service.get_vendor_owned_campaign_or_404(vendor, campaign_public_id)
    data = campaign.to_public_dict()
    data["performance"] = ad_service.campaign_performance(campaign)
    return success({"campaign": data})


@vendor_ads_bp.patch("/<campaign_public_id>")
@require_role(UserRole.VENDOR.value)
def update_campaign(campaign_public_id):
    vendor = get_or_create_vendor(current_user())
    campaign = ad_service.get_vendor_owned_campaign_or_404(vendor, campaign_public_id)
    data = update_schema.load(request.get_json(silent=True) or {})
    campaign = ad_service.update_campaign(campaign, data)
    return success({"campaign": campaign.to_public_dict()}, message="Campaign updated.")


@vendor_ads_bp.post("/<campaign_public_id>/pause")
@require_role(UserRole.VENDOR.value)
def pause_campaign(campaign_public_id):
    vendor = get_or_create_vendor(current_user())
    campaign = ad_service.get_vendor_owned_campaign_or_404(vendor, campaign_public_id)
    campaign = ad_service.pause_campaign(campaign)
    return success({"campaign": campaign.to_public_dict()}, message="Campaign paused.")


@vendor_ads_bp.post("/<campaign_public_id>/resume")
@require_role(UserRole.VENDOR.value)
def resume_campaign(campaign_public_id):
    vendor = get_or_create_vendor(current_user())
    campaign = ad_service.get_vendor_owned_campaign_or_404(vendor, campaign_public_id)
    campaign = ad_service.resume_campaign(campaign)
    return success({"campaign": campaign.to_public_dict()}, message="Campaign resumed.")


@vendor_ads_bp.post("/<campaign_public_id>/cancel")
@require_role(UserRole.VENDOR.value)
def cancel_campaign(campaign_public_id):
    vendor = get_or_create_vendor(current_user())
    campaign = ad_service.get_vendor_owned_campaign_or_404(vendor, campaign_public_id)
    campaign = ad_service.cancel_campaign(campaign)
    return success({"campaign": campaign.to_public_dict()}, message="Campaign cancelled.")
