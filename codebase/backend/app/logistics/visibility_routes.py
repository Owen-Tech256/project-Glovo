from flask import Blueprint

from app.auth.decorators import require_role, current_user
from app.common.responses import success
from app.logistics import tracking_service
from app.vendors.helpers import get_or_create_vendor

# GET /api/v1/orders/<order_id>/delivery - customer's own order.
order_delivery_bp = Blueprint("order_delivery", __name__, url_prefix="/api/v1/orders")

# GET /api/v1/vendor/orders/<order_id>/delivery - vendor's own branch.
vendor_delivery_bp = Blueprint("vendor_delivery", __name__, url_prefix="/api/v1/vendor")


@order_delivery_bp.route("/<order_id>/delivery", methods=["GET"])
@require_role("CUSTOMER")
def get_order_delivery(order_id):
    delivery = tracking_service.get_delivery_for_customer(current_user(), order_id)
    return success(tracking_service.serialize_delivery_tracking(delivery))


@vendor_delivery_bp.route("/orders/<order_id>/delivery", methods=["GET"])
@require_role("VENDOR")
def get_vendor_order_delivery(order_id):
    vendor = get_or_create_vendor(current_user())
    delivery = tracking_service.get_delivery_for_vendor_by_order(vendor, order_id)
    return success(tracking_service.serialize_delivery_tracking(delivery))
