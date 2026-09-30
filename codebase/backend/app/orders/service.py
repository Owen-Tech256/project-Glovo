"""
Checkout + order business logic. Three things live here rather than in
routes.py, per the Phase 3 implementation prompt's service-layer guidance:

1. `build_checkout_context` / `validate_checkout` / `get_checkout_summary` -
   the read-only checkout preview path. All three share one function so a
   "validate" call and the "summary" a customer sees immediately before
   placing the order can never disagree.
2. `create_order` - the one atomic, transactional path that turns a cart
   into an order. Everything the SRS calls out (revalidate cart, recompute
   totals server-side, snapshot the address, initialize the state machine,
   convert the cart, idempotency-safe) happens inside this single function.
3. Role-scoped read/query and transition helpers for the customer, vendor,
   and admin order endpoints.
"""
import secrets
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.common.errors import NotFoundError, ValidationAppError, ConflictError
from app.models.branch import Branch
from app.models.customer_address import CustomerAddress
from app.models.cart import Cart, CartStatus
from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.models.order_status_history import OrderStatusHistory
from app.models.order_address_snapshot import OrderAddressSnapshot
from app.models.order_promotion import OrderPromotion
from app.cart.pricing import price_cart
from app.orders import state_machine
from app.promotions import service as promotion_service
from app.payments.ledger_service import default_currency


# --- Shared lookups -----------------------------------------------------

def _get_branch_or_404(branch_public_id: str) -> Branch:
    branch = Branch.query.filter_by(public_id=branch_public_id).first()
    if branch is None:
        raise NotFoundError("Branch not found.")
    return branch


def _get_owned_address_or_404(customer, address_public_id: str) -> CustomerAddress:
    address = CustomerAddress.query.filter_by(public_id=address_public_id, user_id=customer.id).first()
    if address is None:
        raise NotFoundError("Address not found.")
    return address


def _delivery_fee() -> Decimal:
    from flask import current_app

    return Decimal(str(current_app.config.get("DELIVERY_FEE_FLAT", "2.99")))


def _generate_order_number() -> str:
    return f"ORD-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(4).upper()}"


def _unique_order_number() -> str:
    for _ in range(5):
        candidate = _generate_order_number()
        if Order.query.filter_by(public_order_number=candidate).first() is None:
            return candidate
    # Vanishingly unlikely fallback with a wider random component.
    return f"ORD-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{secrets.token_hex(6).upper()}"


# --- Checkout preview (validate / summary) -------------------------------

def build_checkout_context(customer, branch_public_id: str, address_public_id: str):
    branch = _get_branch_or_404(branch_public_id)
    address = _get_owned_address_or_404(customer, address_public_id)
    cart = Cart.query.filter_by(customer_id=customer.id, branch_id=branch.id, status=CartStatus.ACTIVE).first()

    issues: list[dict] = []
    priced = None
    if cart is None or cart.items.count() == 0:
        issues.append({"cart_item_id": None, "product_name": None, "reason": "CART_EMPTY"})
    else:
        priced = price_cart(cart)
        issues.extend(priced.issues)

    if not branch.is_served_at(float(address.latitude), float(address.longitude)):
        issues.append({"cart_item_id": None, "product_name": None, "reason": "ADDRESS_OUT_OF_RANGE"})

    return branch, cart, address, priced, issues


def validate_checkout(customer, branch_public_id: str, address_public_id: str) -> dict:
    _branch, cart, _address, priced, issues = build_checkout_context(customer, branch_public_id, address_public_id)
    subtotal = priced.subtotal if priced else Decimal("0")
    is_valid = not issues
    fees = _delivery_fee() if is_valid else Decimal("0")
    discount = Decimal("0")
    if is_valid and cart is not None:
        discount, _promotion, _issue = promotion_service.price_cart_with_promotion(cart, priced, fees)
    return {
        "is_valid": is_valid,
        "issues": issues,
        "subtotal": str(subtotal),
        "fees": str(fees),
        "discount_total": str(discount),
        "total": str(subtotal - discount + fees),
    }


def get_checkout_summary(customer, branch_public_id: str, address_public_id: str) -> dict:
    branch, cart, address, priced, issues = build_checkout_context(customer, branch_public_id, address_public_id)
    subtotal = priced.subtotal if priced else Decimal("0")
    fees = _delivery_fee()
    discount, promotion, promo_issue = (
        promotion_service.price_cart_with_promotion(cart, priced, fees) if cart and priced else (Decimal("0"), None, None)
    )
    return {
        "branch": {"id": branch.public_id, "name": branch.name},
        "address": address.to_public_dict(),
        "cart": cart.to_public_dict() if cart else None,
        "subtotal": str(subtotal),
        "fees": str(fees),
        "discount_total": str(discount),
        "total": str(subtotal - discount + fees),
        "applied_promotion": promotion.to_public_dict() if promotion else None,
        "promotion_issue": promo_issue,
        "is_valid": not issues,
        "issues": issues,
    }


# --- Order creation (atomic) ---------------------------------------------

def create_order(customer, branch_public_id: str, address_public_id: str, idempotency_key: str | None = None):
    """Returns (order, was_created). was_created is False when an existing
    order with the same idempotency_key was replayed instead of a new one
    being made."""
    if idempotency_key:
        existing = Order.query.filter_by(customer_id=customer.id, idempotency_key=idempotency_key).first()
        if existing is not None:
            return existing, False

    branch = _get_branch_or_404(branch_public_id)
    address = _get_owned_address_or_404(customer, address_public_id)

    # with_for_update: serializes concurrent checkout attempts against the
    # same cart on Postgres. SQLite (used in tests) has no row-locking and
    # silently no-ops this, which is fine - tests exercise the logic, not
    # cross-connection concurrency.
    cart = (
        Cart.query.filter_by(customer_id=customer.id, branch_id=branch.id, status=CartStatus.ACTIVE)
        .with_for_update()
        .first()
    )
    if cart is None or cart.items.count() == 0:
        raise ValidationAppError("Your cart is empty.", code="CART_EMPTY")

    priced = price_cart(cart)
    issues = list(priced.issues)
    if not branch.is_served_at(float(address.latitude), float(address.longitude)):
        issues.append({"cart_item_id": None, "product_name": None, "reason": "ADDRESS_OUT_OF_RANGE"})
    if issues:
        raise ValidationAppError(
            "Your order could not be placed. Please review the issues below.",
            code="CHECKOUT_INVALID",
            details={"issues": issues},
        )

    fees = _delivery_fee()
    subtotal = priced.subtotal
    applied_promotion_id = cart.applied_promotion_id

    try:
        order = Order(
            public_order_number=_unique_order_number(),
            customer_id=customer.id,
            branch_id=branch.id,
            source_cart_id=cart.id,
            status=OrderStatus.CREATED,
            subtotal=subtotal,
            fees=fees,
            discount_total=Decimal("0"),
            total=subtotal + fees,
            idempotency_key=idempotency_key,
        )
        db.session.add(order)
        db.session.flush()  # assigns order.id for the child rows below

        # reserve_usage row-locks the Promotion and re-validates it at the
        # instant of order creation (not just at cart-apply time) - see its
        # docstring in app/promotions/service.py. discount_total/total are
        # only ever set from this authoritative recomputation, never from
        # whatever the cart view last showed the customer.
        reservation = promotion_service.reserve_usage(applied_promotion_id, customer, priced, fees, order)
        if reservation is not None:
            discount, promotion = reservation
            order.discount_total = discount
            order.total = subtotal - discount + fees
            db.session.add(
                OrderPromotion(
                    order_id=order.id,
                    promotion_id=promotion.id,
                    code_snapshot=promotion.code,
                    name_snapshot=promotion.name,
                    type_snapshot=promotion.type.value,
                    value_snapshot=promotion.value,
                    discount_amount=discount,
                    currency=default_currency(),
                )
            )

        for item in cart.items.all():
            unit_price = item.branch_product.effective_price
            db.session.add(
                OrderItem(
                    order_id=order.id,
                    product_id=item.product_id,
                    product_name_snapshot=item.product.name,
                    sku_snapshot=item.product.sku,
                    unit_price=unit_price,
                    quantity=item.quantity,
                    line_total=unit_price * item.quantity,
                )
            )

        db.session.add(OrderAddressSnapshot.from_customer_address(order.id, address))

        db.session.add(
            OrderStatusHistory(
                order_id=order.id,
                from_status=None,
                to_status=OrderStatus.CREATED.value,
                changed_by_user_id=customer.id,
                reason="Order placed by customer.",
            )
        )

        # Phase 3 had no payment gateway integration, so this used to also
        # auto-transition straight to PAYMENT_CONFIRMED here (see the
        # backend README / previous-phase notes). Phase 5 replaces that
        # placeholder with a real payment flow: the order now stops at
        # PENDING_PAYMENT and only app/payments/payment_service.py's
        # confirm_payment_success - triggered by an actual successful
        # payment - may ever move it to PAYMENT_CONFIRMED.
        state_machine.apply_transition(
            order, OrderStatus.PENDING_PAYMENT, actor_user=None,
            reason="Order created; awaiting payment.",
        )

        cart.status = CartStatus.CONVERTED

        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        if idempotency_key:
            existing = Order.query.filter_by(customer_id=customer.id, idempotency_key=idempotency_key).first()
            if existing is not None:
                return existing, False
        raise ConflictError("A conflicting order already exists for this request.", code="ORDER_CONFLICT")
    except Exception:
        db.session.rollback()
        raise

    return order, True


# --- Customer-facing order access ----------------------------------------

def get_owned_order_or_404(customer, order_public_id: str) -> Order:
    order = Order.query.filter_by(public_id=order_public_id, customer_id=customer.id).first()
    if order is None:
        raise NotFoundError("Order not found.")
    return order


def list_customer_orders(customer, status: str | None = None, page: int = 1, per_page: int = 20):
    query = Order.query.filter_by(customer_id=customer.id)
    if status:
        query = query.filter(Order.status == status)
    return query.order_by(Order.created_at.desc()).paginate(
        page=max(page, 1), per_page=max(min(per_page, 100), 1), error_out=False
    )


def cancel_order(customer, order_public_id: str, reason: str | None) -> Order:
    order = get_owned_order_or_404(customer, order_public_id)
    state_machine.apply_cancellation(order, actor_user=customer, reason=reason or "Cancelled by customer.")
    # Frees this customer's promotion slot back up, in the same
    # transaction as the cancellation itself - see its docstring in
    # app/promotions/service.py.
    promotion_service.release_usage_for_order(order)
    db.session.commit()
    return order


def get_order_status_history(order: Order) -> list[OrderStatusHistory]:
    return order.status_history.all()


# --- Vendor-facing order access -------------------------------------------

def get_vendor_order_or_404(vendor, order_public_id: str) -> Order:
    order = Order.query.filter_by(public_id=order_public_id).first()
    if order is None or order.branch.vendor_id != vendor.id:
        raise NotFoundError("Order not found.")
    return order


def list_vendor_orders(vendor, branch_public_id: str | None = None, status: str | None = None,
                        page: int = 1, per_page: int = 20):
    query = Order.query.join(Branch).filter(Branch.vendor_id == vendor.id)
    if branch_public_id:
        query = query.filter(Branch.public_id == branch_public_id)
    if status:
        query = query.filter(Order.status == status)
    return query.order_by(Order.created_at.desc()).paginate(
        page=max(page, 1), per_page=max(min(per_page, 100), 1), error_out=False
    )


def vendor_transition_order(vendor, order_public_id: str, to_status: str, vendor_user, reason: str | None) -> Order:
    order = get_vendor_order_or_404(vendor, order_public_id)
    target_status = OrderStatus(to_status)
    state_machine.apply_vendor_transition(order, target_status, vendor_user=vendor_user, reason=reason)
    db.session.commit()

    if target_status == OrderStatus.VENDOR_ACCEPTED:
        from app.notifications.events import notify
        from app.models.notification import NotificationCategory

        notify(
            order.customer, NotificationCategory.ORDER, template_key="order_accepted",
            context={"order_number": order.public_order_number, "vendor_name": vendor.name},
            entity_type="ORDER", entity_id=order.public_id,
        )

    if target_status == OrderStatus.READY:
        # Phase 4: hand the order off to the logistics layer the instant a
        # vendor marks it READY. A separate commit on purpose - the order's
        # own READY transition must succeed and be durable regardless of
        # whether dispatch immediately finds a rider (see
        # app/logistics/dispatch_service.py:create_delivery_and_dispatch,
        # which is idempotent and safe to no-op on retry).
        from app.logistics.dispatch_service import create_delivery_and_dispatch

        create_delivery_and_dispatch(order)

    return order


# --- Admin oversight (read-only) -------------------------------------------

def get_any_order_or_404(order_public_id: str) -> Order:
    order = Order.query.filter_by(public_id=order_public_id).first()
    if order is None:
        raise NotFoundError("Order not found.")
    return order


def list_all_orders(status: str | None = None, branch_public_id: str | None = None,
                     customer_public_id: str | None = None, page: int = 1, per_page: int = 20):
    from app.models.user import User

    query = Order.query
    if status:
        query = query.filter(Order.status == status)
    if branch_public_id:
        query = query.join(Branch).filter(Branch.public_id == branch_public_id)
    if customer_public_id:
        query = query.join(User, Order.customer_id == User.id).filter(User.public_id == customer_public_id)
    return query.order_by(Order.created_at.desc()).paginate(
        page=max(page, 1), per_page=max(min(per_page, 100), 1), error_out=False
    )
