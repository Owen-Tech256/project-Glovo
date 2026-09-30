"""
Single source of truth for "what does this cart currently cost, and is
every line still purchasable". Used by both `Cart.to_public_dict()` (so a
customer's cart view always reflects live prices/availability) and the
checkout validation/order-creation path (app/orders/service.py), so a cart
page and a checkout page can never silently disagree about the total.

Nothing here trusts anything the client sent - every price and every
availability flag is read fresh from `Product` / `BranchProduct` /
`Branch` on each call.
"""
from dataclasses import dataclass, field
from decimal import Decimal

from app.models.branch import BranchStatus
from app.models.product import ProductStatus
from app.models.branch_product import BranchProductAvailability


@dataclass
class CartIssue:
    cart_item_id: str
    product_name: str | None
    reason: str  # machine-readable, one of the codes below

    def to_dict(self) -> dict:
        return {"cart_item_id": self.cart_item_id, "product_name": self.product_name, "reason": self.reason}


@dataclass
class PricedLine:
    product_id: int
    category_id: int | None
    branch_id: int
    quantity: int
    line_total: Decimal


@dataclass
class PricedCart:
    subtotal: Decimal
    item_count: int
    issues: list = field(default_factory=list)  # list[dict] - already serialized
    # Phase 6: per-line breakdown of every line that *did* price
    # successfully (excludes lines already reported in `issues`) - used by
    # app/promotions/service.py to figure out which lines a
    # product/category/branch-scoped promotion is even eligible against,
    # without re-deriving cart contents a second time.
    lines: list = field(default_factory=list)  # list[PricedLine]

    @property
    def is_valid(self) -> bool:
        return not self.issues


def price_cart(cart) -> PricedCart:
    """Prices every ACTIVE, valid line in `cart` against live catalog data.
    Invalid lines (inactive product, unavailable at branch, closed branch)
    are excluded from the subtotal and reported in `issues` rather than
    raising - callers decide whether an issue is fatal (checkout) or just
    informational (cart view)."""
    subtotal = Decimal("0")
    item_count = 0
    issues: list[dict] = []
    lines: list[PricedLine] = []

    branch_active = cart.branch is not None and cart.branch.status == BranchStatus.ACTIVE
    if not branch_active:
        issues.append({"cart_item_id": None, "product_name": None, "reason": "BRANCH_UNAVAILABLE"})

    items = cart.items.all() if hasattr(cart.items, "all") else list(cart.items)
    for item in items:
        product = item.product
        branch_product = item.branch_product
        product_ok = product is not None and product.status == ProductStatus.ACTIVE
        branch_product_ok = (
            branch_product is not None and branch_product.availability_status == BranchProductAvailability.AVAILABLE
        )

        if not (branch_active and product_ok and branch_product_ok):
            issues.append(
                {
                    "cart_item_id": item.public_id,
                    "product_name": product.name if product else None,
                    "reason": "PRODUCT_UNAVAILABLE" if branch_active else "BRANCH_UNAVAILABLE",
                }
            )
            continue

        unit_price = branch_product.effective_price
        subtotal += unit_price * item.quantity
        item_count += item.quantity
        lines.append(
            PricedLine(
                product_id=item.product_id,
                category_id=product.category_id,
                branch_id=cart.branch_id,
                quantity=item.quantity,
                line_total=unit_price * item.quantity,
            )
        )

    return PricedCart(subtotal=subtotal, item_count=item_count, issues=issues, lines=lines)
