import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class DeliveryAssignmentStatus(str, enum.Enum):
    OFFERED = "OFFERED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    # Set on every other still-OFFERED sibling the instant one rider in the
    # same offer batch accepts, so exactly one row per delivery ever ends
    # ACCEPTED. See app/logistics/dispatch_service.py:accept_offer.
    CANCELLED = "CANCELLED"


class DeliveryAssignment(db.Model, PublicIdMixin, TimestampMixin):
    """One dispatch offer to one rider for one delivery. The dispatch engine
    broadcasts an offer batch (DISPATCH_OFFER_BATCH_SIZE candidates) as
    several OFFERED rows for the same delivery_id; whichever rider accepts
    first wins (protected by a row lock on the parent Delivery - see
    dispatch_service.accept_offer), and every sibling offer is flipped to
    CANCELLED in the same transaction."""

    __tablename__ = "delivery_assignments"

    id = db.Column(db.Integer, primary_key=True)
    delivery_id = db.Column(
        db.Integer, db.ForeignKey("deliveries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rider_id = db.Column(db.Integer, db.ForeignKey("riders.id", ondelete="CASCADE"), nullable=False, index=True)

    status = db.Column(
        db.Enum(DeliveryAssignmentStatus, name="delivery_assignment_status", native_enum=False, length=20),
        nullable=False,
        default=DeliveryAssignmentStatus.OFFERED,
        index=True,
    )
    offered_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    responded_at = db.Column(db.DateTime(timezone=True), nullable=True)
    rejection_reason = db.Column(db.String(255), nullable=True)

    rider = db.relationship("Rider")

    __table_args__ = (
        db.Index("ix_delivery_assignments_delivery_status", "delivery_id", "status"),
        db.Index("ix_delivery_assignments_rider_status", "rider_id", "status"),
    )

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "delivery_id": self.delivery.public_id if self.delivery else None,
            "status": self.status.value if isinstance(self.status, DeliveryAssignmentStatus) else self.status,
            "offered_at": self.offered_at.isoformat() if self.offered_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "responded_at": self.responded_at.isoformat() if self.responded_at else None,
            "rejection_reason": self.rejection_reason,
        }

    def __repr__(self):  # pragma: no cover
        return f"<DeliveryAssignment delivery_id={self.delivery_id} rider_id={self.rider_id} {self.status}>"
