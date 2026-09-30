from flask import Blueprint, request

from app.common.responses import success
from app.auth.decorators import require_role, current_user
from app.models.user import UserRole
from app.orders.schemas import CheckoutRequestSchema, CreateOrderSchema, CancelOrderSchema
from app.orders import service as order_service

checkout_bp = Blueprint("checkout", __name__, url_prefix="/api/v1/checkout")
orders_bp = Blueprint("orders", __name__, url_prefix="/api/v1/orders")

checkout_request_schema = CheckoutRequestSchema()
create_order_schema = CreateOrderSchema()
cancel_order_schema = CancelOrderSchema()


# --- Checkout preview ------------------------------------------------------

@checkout_bp.post("/validate")
@require_role(UserRole.CUSTOMER.value)
def validate_checkout():
    user = current_user()
    data = checkout_request_schema.load(request.get_json(silent=True) or {})
    result = order_service.validate_checkout(user, data["branch_id"], data["address_id"])
    return success(result)


@checkout_bp.get("/summary")
@require_role(UserRole.CUSTOMER.value)
def checkout_summary():
    user = current_user()
    data = checkout_request_schema.load(request.args)
    result = order_service.get_checkout_summary(user, data["branch_id"], data["address_id"])
    return success(result)


# --- Orders (checkout finalization + customer order history) --------------

@orders_bp.post("")
@require_role(UserRole.CUSTOMER.value)
def create_order():
    user = current_user()
    data = create_order_schema.load(request.get_json(silent=True) or {})
    order, was_created = order_service.create_order(
        user, data["branch_id"], data["address_id"], data.get("idempotency_key")
    )
    message = "Order placed." if was_created else "Order already placed for this request."
    return success({"order": order.to_public_dict()}, message=message, status_code=201 if was_created else 200)


@orders_bp.get("")
@require_role(UserRole.CUSTOMER.value)
def list_orders():
    user = current_user()
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=20, type=int)
    status_filter = request.args.get("status")

    pagination = order_service.list_customer_orders(user, status=status_filter, page=page, per_page=per_page)
    return success(
        {
            "orders": [o.to_public_dict(include_items=False, include_address=False) for o in pagination.items],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "total_pages": pagination.pages,
            },
        }
    )


@orders_bp.get("/<order_public_id>")
@require_role(UserRole.CUSTOMER.value)
def get_order(order_public_id):
    user = current_user()
    order = order_service.get_owned_order_or_404(user, order_public_id)
    return success({"order": order.to_public_dict()})


@orders_bp.post("/<order_public_id>/cancel")
@require_role(UserRole.CUSTOMER.value)
def cancel_order(order_public_id):
    user = current_user()
    data = cancel_order_schema.load(request.get_json(silent=True) or {})
    order = order_service.cancel_order(user, order_public_id, data.get("reason"))
    return success({"order": order.to_public_dict()}, message="Order cancelled.")


@orders_bp.get("/<order_public_id>/status-history")
@require_role(UserRole.CUSTOMER.value)
def order_status_history(order_public_id):
    user = current_user()
    order = order_service.get_owned_order_or_404(user, order_public_id)
    history = order_service.get_order_status_history(order)
    return success({"history": [h.to_public_dict() for h in history]})
