from app.extensions import db
from app.models.base import PublicIdMixin, _utcnow


class CommissionSnapshot(db.Model, PublicIdMixin):
    """The immutable record of exactly which rule, rate and amount were
    applied at settlement time (SRS 7: "Snapshot the applied rule, rate and
    calculated amount"). Once written this row is never updated - if the
    originating CommissionRule is edited or deactivated afterwards,
    rate_snapshot/fixed_snapshot/calculated_amount here are unaffected, so
    `commission_amount` is always reproducible from stored data alone
    (SRS 18 acceptance criterion 3), independent of the rule's current
    state. `commission_rule_id` is nullable so a snapshot never becomes
    unreadable if a rule row is ever removed.
    """

    __tablename__ = "commission_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    financial_transaction_id = db.Column(
        db.Integer, db.ForeignKey("financial_transactions.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    commission_rule_id = db.Column(
        db.Integer, db.ForeignKey("commission_rules.id", ondelete="SET NULL"), nullable=True, index=True
    )

    rate_snapshot = db.Column(db.Numeric(6, 4), nullable=False)
    fixed_snapshot = db.Column(db.Numeric(12, 2), nullable=False)
    calculated_amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)

    commission_rule = db.relationship("CommissionRule")

    __table_args__ = (
        db.CheckConstraint("calculated_amount >= 0", name="ck_commission_snapshots_amount_non_negative"),
    )

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "commission_rule_id": self.commission_rule.public_id if self.commission_rule else None,
            "rate_snapshot": str(self.rate_snapshot),
            "fixed_snapshot": str(self.fixed_snapshot),
            "calculated_amount": str(self.calculated_amount),
            "currency": self.currency,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<CommissionSnapshot financial_transaction_id={self.financial_transaction_id} amount={self.calculated_amount}>"
