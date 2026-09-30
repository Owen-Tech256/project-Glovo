from flask import Blueprint, request

from app.common.responses import success
from app.auth.decorators import require_role, current_user
from app.models.user import UserRole
from app.models.ad_event import AdEventType
from app.advertising import service as ad_service
from app.advertising.schemas import AdEventSchema

ads_bp = Blueprint("ads", __name__, url_prefix="/api/v1/ads")

event_schema = AdEventSchema()


@ads_bp.post("/campaigns/<campaign_public_id>/events")
@require_role(UserRole.CUSTOMER.value, UserRole.VENDOR.value, UserRole.RIDER.value)
def record_ad_event(campaign_public_id):
    """Tracking beacon fired by the storefront when a sponsored placement
    is rendered (IMPRESSION) or tapped (CLICK). Any authenticated role may
    call this - it's the customer-facing catalog/discovery surface that
    triggers it, not a vendor/admin action."""
    user = current_user()
    data = event_schema.load(request.get_json(silent=True) or {})
    event = ad_service.record_event(
        campaign_public_id, AdEventType(data["event_type"]), user, data.get("event_reference")
    )
    return success({"event": event.to_public_dict()}, status_code=201)
