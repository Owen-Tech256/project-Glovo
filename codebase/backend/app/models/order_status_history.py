from app.extensions import db
from app.models.base import _utcnow


class OrderStatusHistory(db.Model):
    """Append-only audit trail of every order-state transition.

    Mirrors the shape of `AuditEvent` (Phase 1): no `PublicIdMixin`, no
    `updated_at` - a history row is written once and never modified.
    `changed_by_user_id` is nullable to represent the Phase 3 system-driven
    payment placeholder transitions (see app/orders/state_machine.py),
    which have no human actor.
    """

    __tablename__ = "order_status_history"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)

    from_status = db.Column(db.String(20), nullable=True)
    to_status = db.Column(db.String(20), nullable=False)
    changed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    reason = db.Column(db.String(500), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)

    changed_by = db.relationship("User")

    def to_public_dict(self) -> dict:
        return {
            "from_status": self.from_status,
            "to_status": self.to_status,
            "changed_by": self.changed_by.public_id if self.changed_by else None,
            "changed_by_role": self.changed_by.role.value if self.changed_by else None,
            "reason": self.reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<OrderStatusHistory order_id={self.order_id} {self.from_status}->{self.to_status}>"
