from decimal import Decimal

from flask import Blueprint, request

from app.common.responses import success
from app.common.errors import NotFoundError
from app.auth.decorators import require_role, current_user
from app.models.user import UserRole
from app.models.branch import Branch, BranchStatus
from app.cart.schemas import AddCartItemSchema, UpdateCartItemSchema
from app.cart import service as cart_service
from app.promotions import service as promotion_service
from app.promotions.schemas import PromotionApplySchema

cart_bp = Blueprint("cart", __name__, url_prefix="/api/v1/cart")

add_item_schema = AddCartItemSchema()
update_item_schema = UpdateCartItemSchema()
apply_promotion_schema = PromotionApplySchema()


def _empty_cart_dict(branch: Branch) -> dict:
    """Shape returned for a branch the customer hasn't added anything from
    yet, so the frontend can render an empty-cart state without a 404."""
    return {
        "id": None,
        "branch_id": branch.public_id,
        "branch_name": branch.name,
        "status": "ACTIVE",
        "items": [],
        "subtotal": str(Decimal("0")),
        "item_count": 0,
        "has_issues": False,
        "issues": [],
        "created_at": None,
        "updated_at": None,
    }


@cart_bp.get("")
@require_role(UserRole.CUSTOMER.value)
def get_cart():
    """Without ?branch_id: every active cart the customer currently has
    (one per branch they've started shopping at). With ?branch_id: that
    branch's cart specifically, as an empty-cart shape if none exists yet."""
    user = current_user()
    branch_id = request.args.get("branch_id")

    if branch_id:
        branch = Branch.query.filter_by(public_id=branch_id).first()
        if branch is None:
            raise NotFoundError("Branch not found.")
        cart = cart_service.get_active_cart_for_branch(user, branch_id)
        return success({"cart": cart.to_public_dict() if cart else _empty_cart_dict(branch)})

    carts = cart_service.list_active_carts(user)
    return success({"carts": [c.to_public_dict() for c in carts]})


@cart_bp.post("/items")
@require_role(UserRole.CUSTOMER.value)
def add_cart_item():
    user = current_user()
    data = add_item_schema.load(request.get_json(silent=True) or {})
    item = cart_service.add_item(user, data["branch_id"], data["product_id"], data["quantity"])
    return success({"cart": item.cart.to_public_dict()}, message="Item added to cart.", status_code=201)


@cart_bp.patch("/items/<item_public_id>")
@require_role(UserRole.CUSTOMER.value)
def update_cart_item(item_public_id):
    user = current_user()
    data = update_item_schema.load(request.get_json(silent=True) or {})
    item = cart_service.update_item_quantity(user, item_public_id, data["quantity"])
    return success({"cart": item.cart.to_public_dict()}, message="Cart item updated.")


@cart_bp.delete("/items/<item_public_id>")
@require_role(UserRole.CUSTOMER.value)
def delete_cart_item(item_public_id):
    user = current_user()
    cart_service.remove_item(user, item_public_id)
    return success(message="Item removed from cart.")


@cart_bp.delete("")
@require_role(UserRole.CUSTOMER.value)
def clear_cart():
    user = current_user()
    branch_id = request.args.get("branch_id")
    cart_service.clear_cart(user, branch_id)
    return success(message="Cart cleared.")


def _get_owned_cart_or_404(user, branch_id: str):
    if not branch_id:
        raise NotFoundError("branch_id is required.")
    cart = cart_service.get_active_cart_for_branch(user, branch_id)
    if cart is None:
        raise NotFoundError("No active cart was found for that branch.")
    return cart


@cart_bp.post("/promotion")
@require_role(UserRole.CUSTOMER.value)
def apply_cart_promotion():
    """Attaches a promotion code to the customer's active cart for
    ?branch_id. The discount itself is never trusted from this call -
    every later read (cart view, checkout summary, order creation)
    recomputes it fresh from live promotion rules (see
    app/promotions/service.py:price_cart_with_promotion)."""
    user = current_user()
    branch_id = request.args.get("branch_id")
    cart = _get_owned_cart_or_404(user, branch_id)
    data = apply_promotion_schema.load(request.get_json(silent=True) or {})
    promotion_service.apply_promotion_to_cart(user, cart, data["code"])
    return success({"cart": cart.to_public_dict()}, message="Promotion applied.")


@cart_bp.delete("/promotion")
@require_role(UserRole.CUSTOMER.value)
def remove_cart_promotion():
    user = current_user()
    branch_id = request.args.get("branch_id")
    cart = _get_owned_cart_or_404(user, branch_id)
    promotion_service.remove_promotion_from_cart(cart)
    return success({"cart": cart.to_public_dict()}, message="Promotion removed.")
