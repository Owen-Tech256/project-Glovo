import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin, _utcnow


class DisputeActionType(str, enum.Enum):
    NOTE = "NOTE"
    REQUEST_INFO = "REQUEST_INFO"
    REFUND_ISSUED = "REFUND_ISSUED"
    PARTIAL_REFUND_ISSUED = "PARTIAL_REFUND_ISSUED"
    REPLACEMENT_APPROVED = "REPLACEMENT_APPROVED"
    ESCALATED = "ESCALATED"
    REJECTED = "REJECTED"
    RESOLVED = "RESOLVED"
    REOPENED = "REOPENED"
    OTHER = "OTHER"


FINANCIAL_ACTION_TYPES = (DisputeActionType.REFUND_ISSUED, DisputeActionType.PARTIAL_REFUND_ISSUED)


class DisputeActionStatus(str, enum.Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DisputeAction(db.Model, PublicIdMixin, TimestampMixin):
    """Every decision and action taken on a dispute (SRS 6: "Record actor,
    reason, timestamp and resulting action"), including plain investigation
    notes. `reference_type`/`reference_id` point at whatever the action
    actually produced - e.g. reference_type="REFUND", reference_id=<refund
    public_id> for a REFUND_ISSUED action - so the audit trail links
    straight to the authoritative Phase 5 record rather than duplicating
    its data here."""

    __tablename__ = "dispute_actions"

    id = db.Column(db.Integer, primary_key=True)
    dispute_id = db.Column(db.Integer, db.ForeignKey("disputes.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = db.Column(db.Enum(DisputeActionType, name="dispute_action_type", native_enum=False, length=25), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    reference_type = db.Column(db.String(30), nullable=True)
    reference_id = db.Column(db.String(64), nullable=True)

    reason = db.Column(db.Text, nullable=True)
    status = db.Column(
        db.Enum(DisputeActionStatus, name="dispute_action_status", native_enum=False, length=10),
        nullable=False, default=DisputeActionStatus.COMPLETED,
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    actor = db.relationship("User")

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "action_type": self.action_type.value if isinstance(self.action_type, DisputeActionType) else self.action_type,
            "actor": {"id": self.actor.public_id, "name": self.actor.full_name} if self.actor else None,
            "reference_type": self.reference_type,
            "reference_id": self.reference_id,
            "reason": self.reason,
            "status": self.status.value if isinstance(self.status, DisputeActionStatus) else self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<DisputeAction dispute_id={self.dispute_id} {self.action_type}>"
