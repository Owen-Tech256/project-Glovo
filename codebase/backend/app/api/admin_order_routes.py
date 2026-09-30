from flask import Blueprint, request

from app.common.responses import success
from app.auth.decorators import require_role
from app.models.user import UserRole
from app.orders import service as order_service

admin_orders_bp = Blueprint("admin_orders", __name__, url_prefix="/api/v1/admin/orders")


@admin_orders_bp.get("")
@require_role(UserRole.ADMIN.value)
def list_all_orders():
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=20, type=int)
    status_filter = request.args.get("status")
    branch_id = request.args.get("branch_id")
    customer_id = request.args.get("customer_id")

    pagination = order_service.list_all_orders(
        status=status_filter, branch_public_id=branch_id, customer_public_id=customer_id,
        page=page, per_page=per_page,
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


@admin_orders_bp.get("/<order_public_id>")
@require_role(UserRole.ADMIN.value)
def get_any_order(order_public_id):
    order = order_service.get_any_order_or_404(order_public_id)
    return success({"order": order.to_public_dict()})


@admin_orders_bp.get("/<order_public_id>/status-history")
@require_role(UserRole.ADMIN.value)
def admin_order_status_history(order_public_id):
    order = order_service.get_any_order_or_404(order_public_id)
    history = order_service.get_order_status_history(order)
    return success({"history": [h.to_public_dict() for h in history]})
