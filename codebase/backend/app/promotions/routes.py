from flask import Blueprint

from app.common.responses import success
from app.auth.decorators import require_role
from app.models.user import UserRole
from app.promotions import service as promotion_service

promotions_bp = Blueprint("promotions", __name__, url_prefix="/api/v1/promotions")


@promotions_bp.get("")
@require_role(UserRole.CUSTOMER.value)
def list_promotions():
    """Currently-active, browsable promotions (SRS 4's discovery surface).
    Whether a given one actually applies to what's in the customer's cart
    is only known once they try to apply it (POST /cart/promotion) - this
    endpoint is a catalog, not a per-cart eligibility check."""
    promotions = promotion_service.list_public_promotions()
    return success({"promotions": [p.to_public_dict() for p in promotions]})
