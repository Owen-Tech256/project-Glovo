from flask import Blueprint, request

from app.common.responses import success
from app.auth.decorators import require_role, current_user
from app.models.user import UserRole
from app.vendors.helpers import get_or_create_vendor
from app.orders.schemas import VendorTransitionSchema
from app.orders import service as order_service

vendor_orders_bp = Blueprint("vendor_orders", __name__, url_prefix="/api/v1/vendor/orders")

vendor_transition_schema = VendorTransitionSchema()


@vendor_orders_bp.get("")
@require_role(UserRole.VENDOR.value)
def list_vendor_orders():
    vendor = get_or_create_vendor(current_user())
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=20, type=int)
    status_filter = request.args.get("status")
    branch_id = request.args.get("branch_id")

    pagination = order_service.list_vendor_orders(
        vendor, branch_public_id=branch_id, status=status_filter, page=page, per_page=per_page
    )
    return success(
        {
            "orders": [o.to_public_dict(include_items=False) for o in pagination.items],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "total_pages": pagination.pages,
            },
        }
    )


@vendor_orders_bp.get("/<order_public_id>")
@require_role(UserRole.VENDOR.value)
def get_vendor_order(order_public_id):
    vendor = get_or_create_vendor(current_user())
    order = order_service.get_vendor_order_or_404(vendor, order_public_id)
    return success({"order": order.to_public_dict()})


@vendor_orders_bp.post("/<order_public_id>/transition")
@require_role(UserRole.VENDOR.value)
def transition_vendor_order(order_public_id):
    user = current_user()
    vendor = get_or_create_vendor(user)
    data = vendor_transition_schema.load(request.get_json(silent=True) or {})
    order = order_service.vendor_transition_order(
        vendor, order_public_id, data["to_status"], vendor_user=user, reason=data.get("reason")
    )
    return success({"order": order.to_public_dict()}, message="Order status updated.")


@vendor_orders_bp.get("/<order_public_id>/status-history")
@require_role(UserRole.VENDOR.value)
def vendor_order_status_history(order_public_id):
    vendor = get_or_create_vendor(current_user())
    order = order_service.get_vendor_order_or_404(vendor, order_public_id)
    history = order_service.get_order_status_history(order)
    return success({"history": [h.to_public_dict() for h in history]})
