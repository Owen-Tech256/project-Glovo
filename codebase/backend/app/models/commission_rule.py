import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class CommissionScopeType(str, enum.Enum):
    GLOBAL = "GLOBAL"
    # Reserved for future scoping (SRS 7: "Allow future scoping by vendor,
    # category or other business dimensions... without redesigning the
    # core"). Not resolved by app/payments/commission_service.py in this
    # phase - only GLOBAL rules are ever selected - but scope_type/scope_id
    # already exist on the row so a later phase can start writing
    # VENDOR/CATEGORY rules without a migration.
    VENDOR = "VENDOR"
    CATEGORY = "CATEGORY"


class CommissionRuleStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class CommissionRule(db.Model, PublicIdMixin, TimestampMixin):
    """An admin-configurable platform commission rule (SRS 7). Editing a
    rule in place (percentage_rate/fixed_amount/status) never rewrites
    history: every past calculation already lives in its own immutable
    CommissionSnapshot row, so changing a rule here only affects
    settlements calculated after the change (SRS 7: "Do not change
    historical financial records when commission rules are edited").
    """

    __tablename__ = "commission_rules"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)

    percentage_rate = db.Column(db.Numeric(6, 4), nullable=False, default=0)
    fixed_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    scope_type = db.Column(
        db.Enum(CommissionScopeType, name="commission_scope_type", native_enum=False, length=20),
        nullable=False,
        default=CommissionScopeType.GLOBAL,
        index=True,
    )
    scope_id = db.Column(db.Integer, nullable=True)

    status = db.Column(
        db.Enum(CommissionRuleStatus, name="commission_rule_status", native_enum=False, length=20),
        nullable=False,
        default=CommissionRuleStatus.ACTIVE,
        index=True,
    )
    effective_from = db.Column(db.DateTime(timezone=True), nullable=False)
    effective_to = db.Column(db.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        db.CheckConstraint("percentage_rate >= 0 AND percentage_rate <= 1", name="ck_commission_rules_rate_range"),
        db.CheckConstraint("fixed_amount >= 0", name="ck_commission_rules_fixed_non_negative"),
        db.Index("ix_commission_rules_scope_status", "scope_type", "status"),
    )

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "name": self.name,
            "percentage_rate": str(self.percentage_rate),
            "fixed_amount": str(self.fixed_amount),
            "scope_type": self.scope_type.value if isinstance(self.scope_type, CommissionScopeType) else self.scope_type,
            "scope_id": self.scope_id,
            "status": self.status.value if isinstance(self.status, CommissionRuleStatus) else self.status,
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<CommissionRule {self.public_id} {self.name} rate={self.percentage_rate}>"
