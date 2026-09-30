"""
Promotion CRUD, eligibility evaluation, and redemption (SRS 4).

Three separate concerns live here, deliberately kept apart:

1. `price_cart_with_promotion` - the read-only pricing function. Called
   from Cart.to_public_dict (cart view), app/orders/service.py's checkout
   preview, and order creation. Never trusts or writes anything; always
   re-derives the discount from live promotion rules + live cart contents,
   the same "never trust a stored total" stance app/cart/pricing.py takes.
2. `apply_promotion_to_cart` / `remove_promotion_from_cart` - the two
   customer actions that set/clear Cart.applied_promotion_id.
3. `reserve_usage` / `release_usage_for_order` - the write path, invoked
   only from app/orders/service.py inside the same atomic transaction as
   order creation/cancellation. This is the only place usage limits are
   ever enforced or consumed.

CRUD (vendor/admin) lives at the bottom.
"""
from decimal import Decimal, ROUND_HALF_UP

from app.extensions import db
from app.common.errors import NotFoundError, ValidationAppError, AuthorizationError
from app.models.promotion import (
    Promotion, PromotionScope, PromotionRule, PromotionRuleType, PromotionType,
    PromotionScopeType, PromotionStatus, PromotionUsage, PromotionUsageStatus,
)
from app.models.order import Order, OrderStatus
from app.models.cart import Cart

TWO_PLACES = Decimal("0.01")


def _quantize(amount: Decimal) -> Decimal:
    return amount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


# --- Eligibility -----------------------------------------------------------

def _eligible_subtotal(promotion: Promotion, priced) -> Decimal:
    """The portion of a priced cart's lines this promotion's scope covers.
    ORDER/VENDOR scope (a cart is always single-vendor/single-branch - see
    app/models/cart.py) covers the whole subtotal; BRANCH/CATEGORY/PRODUCT
    scope only the matching lines."""
    if promotion.scope_type in (PromotionScopeType.ORDER, PromotionScopeType.VENDOR):
        return priced.subtotal

    target_ids = {s.target_id for s in promotion.scopes}
    if not target_ids:
        return Decimal("0")

    total = Decimal("0")
    for line in priced.lines:
        if promotion.scope_type == PromotionScopeType.BRANCH and line.branch_id in target_ids:
            total += line.line_total
        elif promotion.scope_type == PromotionScopeType.CATEGORY and line.category_id in target_ids:
            total += line.line_total
        elif promotion.scope_type == PromotionScopeType.PRODUCT and line.product_id in target_ids:
            total += line.line_total
    return total


def _check_rules(promotion: Promotion, priced, customer) -> str | None:
    """Returns an issue code if a PromotionRule fails, else None."""
    for rule in promotion.rules:
        if rule.rule_type == PromotionRuleType.MIN_ITEM_COUNT:
            threshold = int(rule.rule_value or 0)
            if priced.item_count < threshold:
                return "PROMOTION_MIN_ITEMS_NOT_MET"
        elif rule.rule_type == PromotionRuleType.FIRST_ORDER_ONLY:
            has_prior_order = (
                Order.query.filter(Order.customer_id == customer.id, Order.status != OrderStatus.CANCELLED)
                .first()
                is not None
            )
            if has_prior_order:
                return "PROMOTION_FIRST_ORDER_ONLY"
    return None


def _usage_counts(promotion: Promotion, customer_id: int) -> tuple[int, int]:
    """(total_consumed, customer_consumed) - CONSUMED usages only; RELEASED
    ones (from a cancelled order) never count against a limit."""
    total = PromotionUsage.query.filter_by(
        promotion_id=promotion.id, status=PromotionUsageStatus.CONSUMED
    ).count()
    per_customer = PromotionUsage.query.filter_by(
        promotion_id=promotion.id, customer_id=customer_id, status=PromotionUsageStatus.CONSUMED
    ).count()
    return total, per_customer


def evaluate_promotion(promotion: Promotion, priced, customer, fees: Decimal) -> tuple[Decimal, str | None]:
    """Returns (discount_amount, issue_code). discount_amount is always 0
    when issue_code is set. Pure/read-only - does not touch usage counts
    beyond reading them, so it is safe to call from a GET request."""
    if not promotion.is_currently_active:
        return Decimal("0"), "PROMOTION_NOT_ACTIVE"

    if promotion.min_subtotal and priced.subtotal < promotion.min_subtotal:
        return Decimal("0"), "PROMOTION_MIN_SUBTOTAL_NOT_MET"

    rule_issue = _check_rules(promotion, priced, customer)
    if rule_issue:
        return Decimal("0"), rule_issue

    total_used, customer_used = _usage_counts(promotion, customer.id)
    if promotion.usage_limit_total is not None and total_used >= promotion.usage_limit_total:
        return Decimal("0"), "PROMOTION_USAGE_LIMIT_REACHED"
    if promotion.usage_limit_per_customer is not None and customer_used >= promotion.usage_limit_per_customer:
        return Decimal("0"), "PROMOTION_CUSTOMER_LIMIT_REACHED"

    if promotion.type == PromotionType.FREE_DELIVERY:
        discount = fees
    else:
        eligible = _eligible_subtotal(promotion, priced)
        if eligible <= 0:
            return Decimal("0"), "PROMOTION_NOT_APPLICABLE_TO_CART"
        if promotion.type == PromotionType.PERCENTAGE:
            discount = eligible * (promotion.value / Decimal("100"))
            if promotion.max_discount_amount is not None:
                discount = min(discount, promotion.max_discount_amount)
        else:  # FIXED_AMOUNT
            discount = min(promotion.value, eligible)

    discount = _quantize(min(discount, priced.subtotal + fees))
    if discount <= 0:
        return Decimal("0"), "PROMOTION_NOT_APPLICABLE_TO_CART"
    return discount, None


def price_cart_with_promotion(cart: Cart, priced, fees: Decimal = Decimal("0")):
    """Returns (discount_amount, promotion_or_None, issue_or_None) for
    whichever promotion (if any) is currently attached to `cart`. Never
    raises - an applied promotion that has since become invalid (expired,
    limit reached, cart no longer qualifies) just prices at zero discount
    with an issue code the frontend can surface, rather than blocking the
    cart/checkout view."""
    if cart.applied_promotion_id is None:
        return Decimal("0"), None, None

    promotion = db.session.get(Promotion, cart.applied_promotion_id)
    if promotion is None:
        return Decimal("0"), None, None

    discount, issue = evaluate_promotion(promotion, priced, cart.customer, fees)
    return discount, promotion, issue


# --- Customer actions --------------------------------------------------

def apply_promotion_to_cart(customer, cart: Cart, code: str) -> Promotion:
    promotion = Promotion.query.filter_by(code=code.strip().upper()).first()
    if promotion is None:
        raise NotFoundError("No promotion was found with that code.")
    if promotion.vendor_id is not None and promotion.vendor_id != cart.branch.vendor_id:
        raise ValidationAppError("This code is not valid at this vendor.", code="PROMOTION_NOT_APPLICABLE_TO_CART")

    from app.cart.pricing import price_cart
    from app.orders.service import _delivery_fee

    priced = price_cart(cart)
    discount, issue = evaluate_promotion(promotion, priced, customer, _delivery_fee())
    if issue:
        raise ValidationAppError(_ISSUE_MESSAGES.get(issue, "This code cannot be applied to your cart."), code=issue)

    cart.applied_promotion_id = promotion.id
    db.session.commit()
    return promotion


def remove_promotion_from_cart(cart: Cart) -> None:
    cart.applied_promotion_id = None
    db.session.commit()


_ISSUE_MESSAGES = {
    "PROMOTION_NOT_ACTIVE": "This code is no longer active.",
    "PROMOTION_MIN_SUBTOTAL_NOT_MET": "Your order does not meet this code's minimum amount.",
    "PROMOTION_MIN_ITEMS_NOT_MET": "Your cart does not have enough items for this code.",
    "PROMOTION_FIRST_ORDER_ONLY": "This code is only valid on a first order.",
    "PROMOTION_USAGE_LIMIT_REACHED": "This code has reached its usage limit.",
    "PROMOTION_CUSTOMER_LIMIT_REACHED": "You have already used this code.",
    "PROMOTION_NOT_APPLICABLE_TO_CART": "This code does not apply to anything in your cart.",
}


# --- Redemption (called only from app/orders/service.py, inside its own
#     atomic transaction) --------------------------------------------------

def reserve_usage(promotion_id: int, customer, priced, fees: Decimal, order) -> tuple[Decimal, "Promotion"] | None:
    """Row-locks the Promotion, re-validates it, and writes a CONSUMED
    PromotionUsage + returns (discount_amount, promotion). The row lock is
    the serialization point that keeps two concurrent orders from both
    slipping in under a global usage_limit_total (the same "lock the row
    you're about to enforce a limit against" pattern already used by
    app/payments/refund_service.py and app/logistics/dispatch_service.py).
    Raises ValidationAppError if the promotion is no longer valid at the
    instant of order creation (e.g. someone else just used the last slot).
    Returns None if the cart had no promotion attached."""
    if promotion_id is None:
        return None

    promotion = Promotion.query.filter_by(id=promotion_id).with_for_update().first()
    if promotion is None:
        return None

    discount, issue = evaluate_promotion(promotion, priced, customer, fees)
    if issue:
        raise ValidationAppError(
            _ISSUE_MESSAGES.get(issue, "The applied promotion is no longer valid."), code=issue
        )

    usage = PromotionUsage(
        promotion_id=promotion.id,
        customer_id=customer.id,
        order_id=order.id,
        status=PromotionUsageStatus.CONSUMED,
        discount_amount=discount,
    )
    db.session.add(usage)
    promotion.usage_count = (promotion.usage_count or 0) + 1
    return discount, promotion


def release_usage_for_order(order) -> None:
    """Called from app/orders/state_machine.py's cancellation path (via
    app/orders/service.py:cancel_order) so a cancelled order's promotion
    slot is freed back up for the same customer, rather than being
    permanently burned by an order that never completed."""
    usage = PromotionUsage.query.filter_by(order_id=order.id, status=PromotionUsageStatus.CONSUMED).first()
    if usage is None:
        return
    usage.status = PromotionUsageStatus.RELEASED
    promotion = Promotion.query.filter_by(id=usage.promotion_id).with_for_update().first()
    if promotion is not None and promotion.usage_count:
        promotion.usage_count = max(0, promotion.usage_count - 1)


# --- CRUD (vendor / admin) ----------------------------------------------

def _apply_scope_and_rules(promotion: Promotion, scope_target_ids: list | None, rules: list[dict] | None) -> None:
    if scope_target_ids is not None:
        PromotionScope.query.filter_by(promotion_id=promotion.id).delete()
        for target_id in scope_target_ids:
            db.session.add(PromotionScope(promotion_id=promotion.id, target_id=target_id))
    if rules is not None:
        PromotionRule.query.filter_by(promotion_id=promotion.id).delete()
        for rule in rules:
            db.session.add(
                PromotionRule(
                    promotion_id=promotion.id,
                    rule_type=PromotionRuleType(rule["rule_type"]),
                    rule_value=rule.get("rule_value"),
                )
            )


def resolve_scope_target_ids(scope_type: PromotionScopeType, vendor, public_ids: list[str] | None) -> list[int] | None:
    """Client-facing scope_target_ids are public_ids (branches/categories/
    products) - resolves them to the internal integer ids PromotionScope
    stores, and (for a vendor-created promotion) verifies every target
    actually belongs to that vendor, so a vendor can never scope a
    promotion onto another vendor's catalog."""
    if public_ids is None:
        return None
    if scope_type == PromotionScopeType.BRANCH:
        from app.models.branch import Branch

        rows = Branch.query.filter(Branch.public_id.in_(public_ids)).all()
        model_lookup = {r.public_id: r for r in rows}
        owner_id = lambda r: r.vendor_id
    elif scope_type == PromotionScopeType.CATEGORY:
        from app.models.category import Category

        rows = Category.query.filter(Category.public_id.in_(public_ids)).all()
        model_lookup = {r.public_id: r for r in rows}
        owner_id = lambda r: r.vendor_id
    elif scope_type == PromotionScopeType.PRODUCT:
        from app.models.product import Product

        rows = Product.query.filter(Product.public_id.in_(public_ids)).all()
        model_lookup = {r.public_id: r for r in rows}
        owner_id = lambda r: r.category.vendor_id if r.category else None
    else:
        raise ValidationAppError("This scope type does not take specific targets.", code="PROMOTION_SCOPE_INVALID")

    if len(model_lookup) != len(set(public_ids)):
        raise ValidationAppError("One or more scope targets were not found.", code="PROMOTION_SCOPE_TARGET_NOT_FOUND")
    if vendor is not None:
        for row in model_lookup.values():
            if owner_id(row) != vendor.id:
                raise AuthorizationError("A promotion can only be scoped to your own catalog.")
    return [row.id for row in model_lookup.values()]


def create_promotion(vendor, data: dict) -> Promotion:
    """`vendor` is None for an admin-created (platform-wide or
    admin-chosen-vendor) promotion; a Vendor instance for a vendor-created
    one, which is then implicitly pinned to that vendor regardless of the
    scope_type requested (SRS 4: a vendor may only ever discount its own
    catalog)."""
    code = data.get("code")
    if code:
        code = code.strip().upper()
        if Promotion.query.filter_by(code=code).first() is not None:
            raise ValidationAppError("This code is already in use.", code="PROMOTION_CODE_TAKEN")

    scope_type = PromotionScopeType(data.get("scope_type", PromotionScopeType.ORDER.value))
    if vendor is not None and scope_type == PromotionScopeType.VENDOR:
        # A vendor-created promotion is always implicitly vendor-scoped -
        # ORDER (whole cart at that vendor's branch) is the natural
        # equivalent, since a cart never spans vendors anyway.
        scope_type = PromotionScopeType.ORDER

    promotion = Promotion(
        vendor_id=vendor.id if vendor else data.get("vendor_id"),
        created_by_user_id=data.get("created_by_user_id"),
        name=data["name"],
        description=data.get("description"),
        code=code,
        type=PromotionType(data["type"]),
        value=data["value"],
        max_discount_amount=data.get("max_discount_amount"),
        min_subtotal=data.get("min_subtotal"),
        scope_type=scope_type,
        usage_limit_total=data.get("usage_limit_total"),
        usage_limit_per_customer=data.get("usage_limit_per_customer", 1),
        # Unlike ad campaigns, a promotion needs no admin moderation before
        # it can be used (SRS 4 has no "requires approval" flag for
        # promotions the way SRS 5 does for ads) - a vendor/admin creating
        # one is, by itself, the act of publishing it, so it defaults live
        # rather than sitting inert until a separate activation call.
        status=PromotionStatus(data.get("status", PromotionStatus.ACTIVE.value)),
        starts_at=data.get("starts_at"),
        ends_at=data.get("ends_at"),
    )
    db.session.add(promotion)
    db.session.flush()
    resolved_target_ids = resolve_scope_target_ids(scope_type, vendor, data.get("scope_target_ids"))
    _apply_scope_and_rules(promotion, resolved_target_ids, data.get("rules"))
    db.session.commit()
    return promotion


def update_promotion(promotion: Promotion, data: dict, vendor=None) -> Promotion:
    for field in (
        "name", "description", "max_discount_amount", "min_subtotal",
        "usage_limit_total", "usage_limit_per_customer", "starts_at", "ends_at",
    ):
        if field in data:
            setattr(promotion, field, data[field])
    if "value" in data:
        promotion.value = data["value"]
    if "status" in data:
        promotion.status = PromotionStatus(data["status"])
    if "code" in data:
        new_code = data["code"].strip().upper() if data["code"] else None
        if new_code and Promotion.query.filter(Promotion.code == new_code, Promotion.id != promotion.id).first():
            raise ValidationAppError("This code is already in use.", code="PROMOTION_CODE_TAKEN")
        promotion.code = new_code
    resolved_target_ids = resolve_scope_target_ids(promotion.scope_type, vendor, data.get("scope_target_ids"))
    _apply_scope_and_rules(promotion, resolved_target_ids, data.get("rules"))
    db.session.commit()
    return promotion


def get_vendor_owned_promotion_or_404(vendor, promotion_public_id: str) -> Promotion:
    promotion = Promotion.query.filter_by(public_id=promotion_public_id, vendor_id=vendor.id).first()
    if promotion is None:
        raise NotFoundError("Promotion not found.")
    return promotion


def get_any_promotion_or_404(promotion_public_id: str) -> Promotion:
    promotion = Promotion.query.filter_by(public_id=promotion_public_id).first()
    if promotion is None:
        raise NotFoundError("Promotion not found.")
    return promotion


def list_vendor_promotions(vendor, status: str | None = None):
    query = Promotion.query.filter_by(vendor_id=vendor.id)
    if status:
        query = query.filter(Promotion.status == status)
    return query.order_by(Promotion.created_at.desc()).all()


def list_all_promotions(status: str | None = None, vendor_public_id: str | None = None,
                         page: int = 1, per_page: int = 20):
    from app.models.vendor import Vendor

    query = Promotion.query
    if status:
        query = query.filter(Promotion.status == status)
    if vendor_public_id:
        query = query.join(Vendor).filter(Vendor.public_id == vendor_public_id)
    return query.order_by(Promotion.created_at.desc()).paginate(
        page=max(page, 1), per_page=max(min(per_page, 100), 1), error_out=False
    )


def list_public_promotions():
    """Currently-ACTIVE, within-window promotions - what a customer sees
    when browsing available codes (SRS 4's discovery surface). Vendor-
    scoped codes are shown to everyone; app/promotions/service.py's
    evaluate_promotion still enforces vendor-match at apply time."""
    from app.models.base import _utcnow

    now = _utcnow()
    return (
        Promotion.query.filter(
            Promotion.status == PromotionStatus.ACTIVE,
            db.or_(Promotion.starts_at.is_(None), Promotion.starts_at <= now),
            db.or_(Promotion.ends_at.is_(None), Promotion.ends_at >= now),
        )
        .order_by(Promotion.created_at.desc())
        .all()
    )
