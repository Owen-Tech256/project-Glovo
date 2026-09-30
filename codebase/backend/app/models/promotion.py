"""
Promotion definitions (SRS 4). A promotion is created by a vendor (always
implicitly scoped to that vendor) or by an admin (platform-wide or scoped
to any vendor/branch/category/product). Only one promotion may ever be
attached to a cart/order in this phase - see PromotionStackingPolicy below
and app/promotions/service.py - so "stacking" is enforced structurally
rather than needing runtime conflict resolution.
"""
import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin, to_aware_utc, _utcnow


class PromotionType(str, enum.Enum):
    PERCENTAGE = "PERCENTAGE"
    FIXED_AMOUNT = "FIXED_AMOUNT"
    FREE_DELIVERY = "FREE_DELIVERY"


class PromotionScopeType(str, enum.Enum):
    ORDER = "ORDER"        # whole-order subtotal is eligible
    VENDOR = "VENDOR"      # every branch/product of one vendor
    BRANCH = "BRANCH"      # specific branch(es) - see PromotionScope
    CATEGORY = "CATEGORY"  # specific category(ies)
    PRODUCT = "PRODUCT"    # specific product(s)


class PromotionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    EXPIRED = "EXPIRED"
    ARCHIVED = "ARCHIVED"


class PromotionStackingPolicy(str, enum.Enum):
    # This phase enforces EXCLUSIVE structurally: Cart.applied_promotion_id
    # is a single nullable FK, so at most one promotion is ever attached to
    # a cart/order. The column exists so a future multi-promotion phase has
    # an explicit stored policy to read rather than an implicit assumption.
    EXCLUSIVE = "EXCLUSIVE"


class Promotion(db.Model, PublicIdMixin, TimestampMixin):
    __tablename__ = "promotions"

    id = db.Column(db.Integer, primary_key=True)
    # NULL = platform-wide/admin-created promotion. Set = vendor-created,
    # implicitly limited to that vendor's own branches/products regardless
    # of scope_type (app/promotions/service.py enforces this on write).
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id", ondelete="CASCADE"), nullable=True, index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    # A customer-entered code. NULL means this promotion is never applied
    # by code in this phase (automatic/segment-targeted application is a
    # documented out-of-scope reduction - see PHASE_6_NOTES.md).
    code = db.Column(db.String(40), unique=True, nullable=True, index=True)

    type = db.Column(db.Enum(PromotionType, name="promotion_type", native_enum=False, length=20), nullable=False)
    value = db.Column(db.Numeric(10, 2), nullable=False)  # percentage points, or a fixed currency amount
    max_discount_amount = db.Column(db.Numeric(10, 2), nullable=True)  # caps a PERCENTAGE discount
    min_subtotal = db.Column(db.Numeric(10, 2), nullable=True)

    scope_type = db.Column(
        db.Enum(PromotionScopeType, name="promotion_scope_type", native_enum=False, length=20),
        nullable=False, default=PromotionScopeType.ORDER,
    )

    usage_limit_total = db.Column(db.Integer, nullable=True)          # NULL = unlimited
    usage_limit_per_customer = db.Column(db.Integer, nullable=True, default=1)
    # Cached counter for fast reads (list views). app/promotions/service.py
    # always re-derives eligibility from promotion_usages under a row lock
    # at order-creation time - this column is never the source of truth for
    # an enforcement decision, only a display convenience.
    usage_count = db.Column(db.Integer, nullable=False, default=0)

    stacking_policy = db.Column(
        db.Enum(PromotionStackingPolicy, name="promotion_stacking_policy", native_enum=False, length=20),
        nullable=False, default=PromotionStackingPolicy.EXCLUSIVE,
    )
    status = db.Column(
        db.Enum(PromotionStatus, name="promotion_status", native_enum=False, length=20),
        nullable=False, default=PromotionStatus.DRAFT, index=True,
    )

    starts_at = db.Column(db.DateTime(timezone=True), nullable=True)
    ends_at = db.Column(db.DateTime(timezone=True), nullable=True)

    vendor = db.relationship("Vendor")
    scopes = db.relationship("PromotionScope", backref="promotion", lazy="dynamic", cascade="all, delete-orphan")
    rules = db.relationship("PromotionRule", backref="promotion", lazy="dynamic", cascade="all, delete-orphan")

    __table_args__ = (
        db.CheckConstraint("value >= 0", name="ck_promotions_value_non_negative"),
        db.Index("ix_promotions_vendor_status", "vendor_id", "status"),
    )

    @property
    def is_within_window(self) -> bool:
        now = _utcnow()
        if self.starts_at and to_aware_utc(self.starts_at) > now:
            return False
        if self.ends_at and to_aware_utc(self.ends_at) < now:
            return False
        return True

    @property
    def is_currently_active(self) -> bool:
        return self.status == PromotionStatus.ACTIVE and self.is_within_window

    def to_public_dict(self, include_scopes: bool = False) -> dict:
        data = {
            "id": self.public_id,
            "vendor_id": self.vendor.public_id if self.vendor else None,
            "name": self.name,
            "description": self.description,
            "code": self.code,
            "type": self.type.value if isinstance(self.type, PromotionType) else self.type,
            "value": str(self.value),
            "max_discount_amount": str(self.max_discount_amount) if self.max_discount_amount is not None else None,
            "min_subtotal": str(self.min_subtotal) if self.min_subtotal is not None else None,
            "scope_type": self.scope_type.value if isinstance(self.scope_type, PromotionScopeType) else self.scope_type,
            "usage_limit_total": self.usage_limit_total,
            "usage_limit_per_customer": self.usage_limit_per_customer,
            "usage_count": self.usage_count,
            "stacking_policy": self.stacking_policy.value if isinstance(self.stacking_policy, PromotionStackingPolicy) else self.stacking_policy,
            "status": self.status.value if isinstance(self.status, PromotionStatus) else self.status,
            "starts_at": self.starts_at.isoformat() if self.starts_at else None,
            "ends_at": self.ends_at.isoformat() if self.ends_at else None,
            "is_currently_active": self.is_currently_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_scopes:
            data["scope_target_ids"] = [s.target_id for s in self.scopes]
            data["rules"] = [r.to_public_dict() for r in self.rules]
        return data

    def __repr__(self):  # pragma: no cover
        return f"<Promotion {self.public_id} {self.name} {self.status}>"


class PromotionScope(db.Model, TimestampMixin):
    """One eligible target for a non-ORDER-scoped promotion. `target_id` is
    a branches.id / categories.id / products.id depending on the owning
    promotion's scope_type - resolved by app/promotions/service.py, which
    is the single place that knows how to interpret it (mirroring the
    reference_type/reference_id polymorphic pattern already used by
    FinancialTransaction elsewhere in this codebase)."""

    __tablename__ = "promotion_scopes"

    id = db.Column(db.Integer, primary_key=True)
    promotion_id = db.Column(db.Integer, db.ForeignKey("promotions.id", ondelete="CASCADE"), nullable=False, index=True)
    target_id = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("promotion_id", "target_id", name="uq_promotion_scopes_identity"),
    )


class PromotionRuleType(str, enum.Enum):
    FIRST_ORDER_ONLY = "FIRST_ORDER_ONLY"
    MIN_ITEM_COUNT = "MIN_ITEM_COUNT"


class PromotionRule(db.Model, TimestampMixin):
    """An extra eligibility rule beyond the fixed min_subtotal/date-window
    columns on Promotion itself. rule_value is a small string payload
    (e.g. the item-count threshold for MIN_ITEM_COUNT); FIRST_ORDER_ONLY
    needs none."""

    __tablename__ = "promotion_rules"

    id = db.Column(db.Integer, primary_key=True)
    promotion_id = db.Column(db.Integer, db.ForeignKey("promotions.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_type = db.Column(
        db.Enum(PromotionRuleType, name="promotion_rule_type", native_enum=False, length=30), nullable=False
    )
    rule_value = db.Column(db.String(100), nullable=True)

    __table_args__ = (
        db.UniqueConstraint("promotion_id", "rule_type", name="uq_promotion_rules_identity"),
    )

    def to_public_dict(self) -> dict:
        return {
            "rule_type": self.rule_type.value if isinstance(self.rule_type, PromotionRuleType) else self.rule_type,
            "rule_value": self.rule_value,
        }


class PromotionUsageStatus(str, enum.Enum):
    CONSUMED = "CONSUMED"
    RELEASED = "RELEASED"


class PromotionUsage(db.Model, PublicIdMixin, TimestampMixin):
    """One redemption of a promotion by a customer. Created CONSUMED in the
    same atomic transaction as the order it discounts (app/orders/service.py
    create_order, under a row lock on the Promotion - see
    app/promotions/service.py:reserve_usage). Flipped to RELEASED - not
    deleted, so usage history stays auditable - if that order is cancelled
    before payment, freeing the slot back up for the same customer/promotion
    (app/promotions/service.py:release_usage_for_order)."""

    __tablename__ = "promotion_usages"

    id = db.Column(db.Integer, primary_key=True)
    promotion_id = db.Column(db.Integer, db.ForeignKey("promotions.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=True, unique=True, index=True)
    status = db.Column(
        db.Enum(PromotionUsageStatus, name="promotion_usage_status", native_enum=False, length=20),
        nullable=False, default=PromotionUsageStatus.CONSUMED, index=True,
    )
    discount_amount = db.Column(db.Numeric(10, 2), nullable=False)

    __table_args__ = (
        db.Index("ix_promotion_usages_promotion_customer", "promotion_id", "customer_id", "status"),
    )

    def __repr__(self):  # pragma: no cover
        return f"<PromotionUsage promotion_id={self.promotion_id} customer_id={self.customer_id} {self.status}>"
