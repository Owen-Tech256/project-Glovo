from flask import Blueprint, request

from app.common.responses import success
from app.auth.decorators import require_role, current_user
from app.models.user import UserRole
from app.vendors.helpers import get_or_create_vendor
from app.promotions import service as promotion_service
from app.promotions.schemas import PromotionCreateSchema, PromotionUpdateSchema

vendor_promotions_bp = Blueprint("vendor_promotions", __name__, url_prefix="/api/v1/vendor/promotions")

create_schema = PromotionCreateSchema()
update_schema = PromotionUpdateSchema()


@vendor_promotions_bp.get("")
@require_role(UserRole.VENDOR.value)
def list_promotions():
    vendor = get_or_create_vendor(current_user())
    status = request.args.get("status")
    promotions = promotion_service.list_vendor_promotions(vendor, status)
    return success({"promotions": [p.to_public_dict(include_scopes=True) for p in promotions]})


@vendor_promotions_bp.post("")
@require_role(UserRole.VENDOR.value)
def create_promotion():
    vendor = get_or_create_vendor(current_user())
    data = create_schema.load(request.get_json(silent=True) or {})
    promotion = promotion_service.create_promotion(vendor, data)
    return success({"promotion": promotion.to_public_dict(include_scopes=True)}, message="Promotion created.", status_code=201)


@vendor_promotions_bp.get("/<promotion_public_id>")
@require_role(UserRole.VENDOR.value)
def get_promotion(promotion_public_id):
    vendor = get_or_create_vendor(current_user())
    promotion = promotion_service.get_vendor_owned_promotion_or_404(vendor, promotion_public_id)
    return success({"promotion": promotion.to_public_dict(include_scopes=True)})


@vendor_promotions_bp.patch("/<promotion_public_id>")
@require_role(UserRole.VENDOR.value)
def update_promotion(promotion_public_id):
    vendor = get_or_create_vendor(current_user())
    promotion = promotion_service.get_vendor_owned_promotion_or_404(vendor, promotion_public_id)
    data = update_schema.load(request.get_json(silent=True) or {})
    promotion = promotion_service.update_promotion(promotion, data, vendor=vendor)
    return success({"promotion": promotion.to_public_dict(include_scopes=True)}, message="Promotion updated.")
