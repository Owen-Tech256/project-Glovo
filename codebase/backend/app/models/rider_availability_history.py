from app.extensions import db
from app.models.base import _utcnow


class RiderAvailabilityHistory(db.Model):
    """Append-only log of every operational-status change (SRS 7: "Record
    availability changes and reasons"). The rider's *current* status lives
    on `Rider.operational_status`; this table is the audit trail of how it
    got there - manual (rider went online/offline) or system-driven (an
    acceptance made them BUSY, a completed delivery returned them to
    AVAILABLE). Mirrors OrderStatusHistory's shape (Phase 3)."""

    __tablename__ = "rider_availability_history"

    id = db.Column(db.Integer, primary_key=True)
    rider_id = db.Column(db.Integer, db.ForeignKey("riders.id", ondelete="CASCADE"), nullable=False, index=True)

    from_status = db.Column(db.String(20), nullable=True)
    to_status = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.String(255), nullable=True)

    changed_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)

    def to_public_dict(self) -> dict:
        return {
            "from_status": self.from_status,
            "to_status": self.to_status,
            "reason": self.reason,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<RiderAvailabilityHistory rider_id={self.rider_id} {self.from_status}->{self.to_status}>"
