"""
Customer/vendor/rider support tickets (SRS 5). `related_entity_type`/
`related_entity_id` is the same polymorphic-reference pattern used
throughout this codebase (FinancialTransaction.reference_type/_id,
Review.target_type/_id) - resolved to/from a client-facing public_id by
app/support/service.py, which is the only place that knows how to look up
an order/delivery/payment/refund/vendor/rider by internal id.
"""
import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class TicketCategory(str, enum.Enum):
    ORDER_ISSUE = "ORDER_ISSUE"
    PAYMENT_ISSUE = "PAYMENT_ISSUE"
    DELIVERY_ISSUE = "DELIVERY_ISSUE"
    ACCOUNT_ISSUE = "ACCOUNT_ISSUE"
    VENDOR_ISSUE = "VENDOR_ISSUE"
    RIDER_ISSUE = "RIDER_ISSUE"
    GENERAL = "GENERAL"
    OTHER = "OTHER"


class TicketPriority(str, enum.Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TicketStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_FOR_CUSTOMER = "WAITING_FOR_CUSTOMER"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


OPEN_STATUSES = (TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.WAITING_FOR_CUSTOMER)


class RelatedEntityType(str, enum.Enum):
    ORDER = "ORDER"
    DELIVERY = "DELIVERY"
    PAYMENT = "PAYMENT"
    REFUND = "REFUND"
    VENDOR = "VENDOR"
    RIDER = "RIDER"


class SupportTicket(db.Model, PublicIdMixin, TimestampMixin):
    __tablename__ = "support_tickets"

    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(20), unique=True, nullable=False, index=True)

    requester_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    assigned_agent_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    category = db.Column(db.Enum(TicketCategory, name="ticket_category", native_enum=False, length=20), nullable=False)
    priority = db.Column(
        db.Enum(TicketPriority, name="ticket_priority", native_enum=False, length=10),
        nullable=False, default=TicketPriority.NORMAL, index=True,
    )
    status = db.Column(
        db.Enum(TicketStatus, name="ticket_status", native_enum=False, length=25),
        nullable=False, default=TicketStatus.OPEN, index=True,
    )

    subject = db.Column(db.String(200), nullable=False)

    related_entity_type = db.Column(
        db.Enum(RelatedEntityType, name="related_entity_type", native_enum=False, length=20), nullable=True
    )
    related_entity_id = db.Column(db.Integer, nullable=True)

    resolution_summary = db.Column(db.Text, nullable=True)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    closed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    requester = db.relationship("User", foreign_keys=[requester_id])
    assigned_agent = db.relationship("User", foreign_keys=[assigned_agent_id])
    messages = db.relationship(
        "SupportMessage", backref="ticket", lazy="dynamic",
        order_by="SupportMessage.created_at", cascade="all, delete-orphan",
    )
    attachments = db.relationship("SupportAttachment", backref="ticket", lazy="dynamic", cascade="all, delete-orphan")
    dispute = db.relationship("Dispute", backref="ticket", uselist=False)

    __table_args__ = (
        db.Index("ix_support_tickets_status_priority", "status", "priority"),
        db.Index("ix_support_tickets_agent_status", "assigned_agent_id", "status"),
    )

    def related_entity_public_id(self) -> str | None:
        """Resolved lazily (not stored) so a renamed/soft-deleted related
        record never leaves a stale public_id cached on the ticket."""
        if self.related_entity_type is None or self.related_entity_id is None:
            return None
        from app.support.service import resolve_entity_public_id

        return resolve_entity_public_id(self.related_entity_type, self.related_entity_id)

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "ticket_number": self.ticket_number,
            "requester": {
                "id": self.requester.public_id, "name": self.requester.full_name, "role": self.requester.role.value,
            } if self.requester else None,
            "assigned_agent": {
                "id": self.assigned_agent.public_id, "name": self.assigned_agent.full_name,
            } if self.assigned_agent else None,
            "category": self.category.value if isinstance(self.category, TicketCategory) else self.category,
            "priority": self.priority.value if isinstance(self.priority, TicketPriority) else self.priority,
            "status": self.status.value if isinstance(self.status, TicketStatus) else self.status,
            "subject": self.subject,
            "related_entity_type": self.related_entity_type.value if isinstance(self.related_entity_type, RelatedEntityType) else self.related_entity_type,
            "related_entity_id": self.related_entity_public_id(),
            "resolution_summary": self.resolution_summary,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<SupportTicket {self.ticket_number} {self.status}>"


class MessageVisibility(str, enum.Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"


class SupportMessage(db.Model, PublicIdMixin, TimestampMixin):
    """`visibility=INTERNAL` messages are staff-only working notes (SRS 5/
    14: "customer-visible messages versus private internal notes" / "must
    separate internal notes from public messages"). Only a customer/vendor/
    rider requester or an unprivileged agent posts PUBLIC; INTERNAL is only
    ever set by staff with a support-management permission - enforced in
    app/support/service.py:add_message, never trusted from client input
    beyond what the caller's own role/permission allows."""

    __tablename__ = "support_messages"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    body = db.Column(db.Text, nullable=False)
    visibility = db.Column(
        db.Enum(MessageVisibility, name="message_visibility", native_enum=False, length=10),
        nullable=False, default=MessageVisibility.PUBLIC, index=True,
    )

    sender = db.relationship("User")

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "sender": {
                "id": self.sender.public_id, "name": self.sender.full_name, "role": self.sender.role.value,
            } if self.sender else None,
            "body": self.body,
            "visibility": self.visibility.value if isinstance(self.visibility, MessageVisibility) else self.visibility,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<SupportMessage ticket_id={self.ticket_id} {self.visibility}>"


class SupportAttachment(db.Model, PublicIdMixin, TimestampMixin):
    """Record-keeping only, mirroring RiderDocument (Phase 4): `reference`
    is a secure reference to where the file lives in real object storage,
    which this phase does not implement (out of scope, same as Phase 4's
    documents). Access is authorized on every retrieval by
    app/support/service.py against the owning ticket's visibility rules,
    never served as a raw static path."""

    __tablename__ = "support_attachments"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id = db.Column(db.Integer, db.ForeignKey("support_messages.id", ondelete="CASCADE"), nullable=True, index=True)
    uploader_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    reference = db.Column(db.String(500), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(100), nullable=True)

    uploader = db.relationship("User")
    message = db.relationship("SupportMessage")

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "message_id": self.message.public_id if self.message else None,
            "uploader": self.uploader.public_id if self.uploader else None,
            "filename": self.filename,
            "content_type": self.content_type,
            "reference": self.reference,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<SupportAttachment ticket_id={self.ticket_id} {self.filename}>"
