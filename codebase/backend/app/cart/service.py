"""
Cart business logic, kept out of app/cart/routes.py per the Phase 3
implementation prompt ("keep business logic in appropriate service/domain
layers rather than putting the entire workflow inside route handlers").

Every function here takes an already-authenticated `customer` (a User) and
is itself the ownership boundary - a cart_item_id that doesn't belong to
that customer simply doesn't resolve, the same 404-not-403 pattern used
throughout Phase 2 (see app/vendors/helpers.py) to avoid confirming a
resource's existence to a non-owner.
"""
from app.extensions import db
from app.common.errors import NotFoundError, ValidationAppError
from app.models.branch import Branch, BranchStatus
from app.models.product import Product, ProductStatus
from app.models.branch_product import BranchProduct, BranchProductAvailability
from app.models.cart import Cart, CartStatus
from app.models.cart_item import CartItem


def _get_branch_or_404(branch_public_id: str) -> Branch:
    branch = Branch.query.filter_by(public_id=branch_public_id).first()
    if branch is None:
        raise NotFoundError("Branch not found.")
    return branch


def get_or_create_active_cart(customer, branch: Branch) -> Cart:
    cart = Cart.query.filter_by(customer_id=customer.id, branch_id=branch.id, status=CartStatus.ACTIVE).first()
    if cart is None:
        cart = Cart(customer_id=customer.id, branch_id=branch.id, status=CartStatus.ACTIVE)
        db.session.add(cart)
        db.session.flush()
    return cart


def list_active_carts(customer) -> list[Cart]:
    return (
        Cart.query.filter_by(customer_id=customer.id, status=CartStatus.ACTIVE)
        .order_by(Cart.updated_at.desc())
        .all()
    )


def get_active_cart_for_branch(customer, branch_public_id: str) -> Cart | None:
    branch = _get_branch_or_404(branch_public_id)
    return Cart.query.filter_by(customer_id=customer.id, branch_id=branch.id, status=CartStatus.ACTIVE).first()


def _get_owned_cart_item_or_404(customer, item_public_id: str) -> CartItem:
    item = (
        CartItem.query.join(Cart)
        .filter(CartItem.public_id == item_public_id, Cart.customer_id == customer.id)
        .first()
    )
    if item is None:
        raise NotFoundError("Cart item not found.")
    return item


def add_item(customer, branch_public_id: str, product_public_id: str, quantity: int) -> CartItem:
    branch = _get_branch_or_404(branch_public_id)
    if branch.status != BranchStatus.ACTIVE:
        raise ValidationAppError("This branch is not currently accepting orders.", code="BRANCH_UNAVAILABLE")

    product = Product.query.filter_by(public_id=product_public_id, status=ProductStatus.ACTIVE).first()
    if product is None:
        raise NotFoundError("Product not found.")

    branch_product = BranchProduct.query.filter_by(branch_id=branch.id, product_id=product.id).first()
    if branch_product is None or branch_product.availability_status != BranchProductAvailability.AVAILABLE:
        raise ValidationAppError(
            "This product is not available at the selected branch.", code="PRODUCT_UNAVAILABLE"
        )

    cart = get_or_create_active_cart(customer, branch)

    max_quantity = _max_quantity()
    item = CartItem.query.filter_by(cart_id=cart.id, product_id=product.id).first()
    if item is None:
        if quantity > max_quantity:
            raise ValidationAppError(f"Quantity cannot exceed {max_quantity} per item.", code="QUANTITY_LIMIT")
        item = CartItem(
            cart_id=cart.id,
            product_id=product.id,
            branch_product_id=branch_product.id,
            quantity=quantity,
            unit_price_snapshot=branch_product.effective_price,
        )
        db.session.add(item)
    else:
        new_quantity = item.quantity + quantity
        if new_quantity > max_quantity:
            raise ValidationAppError(f"Quantity cannot exceed {max_quantity} per item.", code="QUANTITY_LIMIT")
        item.quantity = new_quantity
        item.unit_price_snapshot = branch_product.effective_price
        item.branch_product_id = branch_product.id

    db.session.commit()
    return item


def _max_quantity() -> int:
    from flask import current_app

    return current_app.config.get("CART_MAX_ITEM_QUANTITY", 20)


def update_item_quantity(customer, item_public_id: str, quantity: int) -> CartItem:
    item = _get_owned_cart_item_or_404(customer, item_public_id)
    max_quantity = _max_quantity()
    if quantity > max_quantity:
        raise ValidationAppError(f"Quantity cannot exceed {max_quantity} per item.", code="QUANTITY_LIMIT")
    item.quantity = quantity
    db.session.commit()
    return item


def remove_item(customer, item_public_id: str) -> None:
    item = _get_owned_cart_item_or_404(customer, item_public_id)
    db.session.delete(item)
    db.session.commit()


def clear_cart(customer, branch_public_id: str | None) -> int:
    """Removes all items from the customer's active cart(s). Returns the
    number of carts cleared. The cart row itself is kept (still ACTIVE, now
    empty) rather than deleted, matching the archive-don't-delete pattern
    used across Phase 2."""
    query = Cart.query.filter_by(customer_id=customer.id, status=CartStatus.ACTIVE)
    if branch_public_id is not None:
        branch = _get_branch_or_404(branch_public_id)
        query = query.filter_by(branch_id=branch.id)

    carts = query.all()
    for cart in carts:
        CartItem.query.filter_by(cart_id=cart.id).delete()
    db.session.commit()
    return len(carts)
