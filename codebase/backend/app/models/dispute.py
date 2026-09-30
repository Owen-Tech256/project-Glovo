"""
Disputes over an order/delivery/payment/refund (SRS 6). A Dispute always
anchors to an Order (the one authoritative record every dispute category
in the SRS traces back to - missing/wrong/damaged item, late/failed
delivery, or a payment issue are all about *an order*); delivery/payment/
refund are optional narrower pointers alongside it. Money never moves from
this module directly - `app/disputes/service.py:resolve_with_refund` only
ever calls into `app.payments.refund_service`, and every resulting refund
is recorded as a DisputeAction referencing it, never as a balance edit
here (SRS 6/14: "Financial actions must call Phase 5 services; never
directly edit balances").
"""
import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class DisputeCategory(str, enum.Enum):
    MISSING_ITEM = "MISSING_ITEM"
    WRONG_ITEM = "WRONG_ITEM"
    DAMAGED_ITEM = "DAMAGED_ITEM"
    LATE_DELIVERY = "LATE_DELIVERY"
    FAILED_DELIVERY = "FAILED_DELIVERY"
    PAYMENT_ISSUE = "PAYMENT_ISSUE"
    SERVICE_COMPLAINT = "SERVICE_COMPLAINT"
    OTHER = "OTHER"


class DisputePriority(str, enum.Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class DisputeStatus(str, enum.Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"
    CLOSED = "CLOSED"


OPEN_STATUSES = (DisputeStatus.OPEN, DisputeStatus.INVESTIGATING, DisputeStatus.ACTION_REQUIRED)


class Dispute(db.Model, PublicIdMixin, TimestampMixin):
    __tablename__ = "disputes"

    id = db.Column(db.Integer, primary_key=True)
    dispute_number = db.Column(db.String(20), unique=True, nullable=False, index=True)

    ticket_id = db.Column(db.Integer, db.ForeignKey("support_tickets.id", ondelete="SET NULL"), nullable=True, unique=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    delivery_id = db.Column(db.Integer, db.ForeignKey("deliveries.id", ondelete="SET NULL"), nullable=True, index=True)
    payment_id = db.Column(db.Integer, db.ForeignKey("payments.id", ondelete="SET NULL"), nullable=True, index=True)
    refund_id = db.Column(db.Integer, db.ForeignKey("refunds.id", ondelete="SET NULL"), nullable=True, index=True)

    opened_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)

    category = db.Column(db.Enum(DisputeCategory, name="dispute_category", native_enum=False, length=20), nullable=False)
    priority = db.Column(
        db.Enum(DisputePriority, name="dispute_priority", native_enum=False, length=10),
        nullable=False, default=DisputePriority.NORMAL, index=True,
    )
    status = db.Column(
        db.Enum(DisputeStatus, name="dispute_status", native_enum=False, length=20),
        nullable=False, default=DisputeStatus.OPEN, index=True,
    )

    description = db.Column(db.Text, nullable=False)
    resolution = db.Column(db.Text, nullable=True)
    resolved_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)

    order = db.relationship("Order")
    delivery = db.relationship("Delivery")
    payment = db.relationship("Payment")
    refund = db.relationship("Refund")
    opener = db.relationship("User", foreign_keys=[opened_by])
    resolver = db.relationship("User", foreign_keys=[resolved_by])
    evidence = db.relationship("DisputeEvidence", backref="dispute", lazy="dynamic", cascade="all, delete-orphan")
    actions = db.relationship(
        "DisputeAction", backref="dispute", lazy="dynamic",
        order_by="DisputeAction.created_at", cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.Index("ix_disputes_status_priority", "status", "priority"),
    )

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "dispute_number": self.dispute_number,
            "ticket_id": self.ticket.public_id if self.ticket else None,
            "order": {"id": self.order.public_id, "number": self.order.public_order_number} if self.order else None,
            "delivery_id": self.delivery.public_id if self.delivery else None,
            "payment_id": self.payment.public_id if self.payment else None,
            "refund_id": self.refund.public_id if self.refund else None,
            "opened_by": {"id": self.opener.public_id, "name": self.opener.full_name, "role": self.opener.role.value} if self.opener else None,
            "category": self.category.value if isinstance(self.category, DisputeCategory) else self.category,
            "priority": self.priority.value if isinstance(self.priority, DisputePriority) else self.priority,
            "status": self.status.value if isinstance(self.status, DisputeStatus) else self.status,
            "description": self.description,
            "resolution": self.resolution,
            "resolved_by": self.resolver.public_id if self.resolver else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<Dispute {self.dispute_number} {self.status}>"
