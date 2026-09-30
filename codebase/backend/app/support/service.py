"""
Support ticket lifecycle (SRS 5): creation, the customer/vendor/rider-vs-
staff messaging split, attachments, assignment, and resolution/closure.

`related_entity_type`/`related_entity_id` resolution is centralized here
(`_resolve_related_entity`/`resolve_entity_public_id`) - the one place
that knows how to look up an order/delivery/payment/refund/vendor/rider by
internal id and, for the order-lifecycle types, verify the requester
actually has standing to reference it. This mirrors the polymorphic-
resolution helpers already established in app/reviews/service.py and
app/promotions/service.py.
"""
import secrets
from datetime import datetime, timezone

from app.extensions import db
from app.common.errors import NotFoundError, ValidationAppError, AuthorizationError
from app.models.user import User, UserRole
from app.models.support_ticket import (
    SupportTicket, SupportMessage, SupportAttachment,
    TicketCategory, TicketPriority, TicketStatus, RelatedEntityType, MessageVisibility, OPEN_STATUSES,
)
from app.rbac.service import has_permission


def _is_staff_viewer(user: User) -> bool:
    return user.role == UserRole.ADMIN and (has_permission(user, "support.view") or has_permission(user, "support.manage"))


def _is_staff_manager(user: User) -> bool:
    return user.role == UserRole.ADMIN and has_permission(user, "support.manage")


# --- Polymorphic related-entity resolution --------------------------------

def _lookup_entity(entity_type: RelatedEntityType, internal_id: int):
    if entity_type == RelatedEntityType.ORDER:
        from app.models.order import Order

        return db.session.get(Order, internal_id)
    if entity_type == RelatedEntityType.DELIVERY:
        from app.models.delivery import Delivery

        return db.session.get(Delivery, internal_id)
    if entity_type == RelatedEntityType.PAYMENT:
        from app.models.payment import Payment

        return db.session.get(Payment, internal_id)
    if entity_type == RelatedEntityType.REFUND:
        from app.models.refund import Refund

        return db.session.get(Refund, internal_id)
    if entity_type == RelatedEntityType.VENDOR:
        from app.models.vendor import Vendor

        return db.session.get(Vendor, internal_id)
    from app.models.rider import Rider

    return db.session.get(Rider, internal_id)


def resolve_entity_public_id(entity_type: RelatedEntityType, internal_id: int) -> str | None:
    row = _lookup_entity(entity_type, internal_id)
    return row.public_id if row is not None else None


def _order_touches_user(order, user: User) -> bool:
    if order.customer_id == user.id:
        return True
    if user.role == UserRole.VENDOR and order.branch.vendor.user_id == user.id:
        return True
    if user.role == UserRole.RIDER and order.delivery and order.delivery.rider and order.delivery.rider.user_id == user.id:
        return True
    return False


def _resolve_related_entity(entity_type: RelatedEntityType, public_id: str, requester: User) -> int:
    if entity_type == RelatedEntityType.ORDER:
        from app.models.order import Order

        row = Order.query.filter_by(public_id=public_id).first()
        if row is None:
            raise NotFoundError("Referenced order not found.")
        if not _order_touches_user(row, requester):
            raise AuthorizationError("You cannot reference an order that isn't yours.")
        return row.id

    if entity_type == RelatedEntityType.DELIVERY:
        from app.models.delivery import Delivery

        row = Delivery.query.filter_by(public_id=public_id).first()
        if row is None:
            raise NotFoundError("Referenced delivery not found.")
        if not _order_touches_user(row.order, requester):
            raise AuthorizationError("You cannot reference a delivery that isn't yours.")
        return row.id

    if entity_type == RelatedEntityType.PAYMENT:
        from app.models.payment import Payment

        row = Payment.query.filter_by(public_id=public_id).first()
        if row is None:
            raise NotFoundError("Referenced payment not found.")
        if not _order_touches_user(row.order, requester):
            raise AuthorizationError("You cannot reference a payment that isn't yours.")
        return row.id

    if entity_type == RelatedEntityType.REFUND:
        from app.models.refund import Refund

        row = Refund.query.filter_by(public_id=public_id).first()
        if row is None:
            raise NotFoundError("Referenced refund not found.")
        if not _order_touches_user(row.order, requester):
            raise AuthorizationError("You cannot reference a refund that isn't yours.")
        return row.id

    if entity_type == RelatedEntityType.VENDOR:
        from app.models.vendor import Vendor

        row = Vendor.query.filter_by(public_id=public_id).first()
        if row is None:
            raise NotFoundError("Referenced vendor not found.")
        return row.id

    from app.models.rider import Rider

    row = Rider.query.filter_by(public_id=public_id).first()
    if row is None:
        raise NotFoundError("Referenced rider not found.")
    return row.id


# --- Tickets ---------------------------------------------------------------

def _generate_ticket_number() -> str:
    return f"TCK-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(4).upper()}"


def _unique_ticket_number() -> str:
    for _ in range(5):
        candidate = _generate_ticket_number()
        if SupportTicket.query.filter_by(ticket_number=candidate).first() is None:
            return candidate
    return f"TCK-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{secrets.token_hex(6).upper()}"


def create_ticket(requester: User, category: str, subject: str, initial_message: str,
                   priority: str | None = None, related_entity_type: str | None = None,
                   related_entity_public_id: str | None = None) -> SupportTicket:
    entity_type_enum = RelatedEntityType(related_entity_type) if related_entity_type else None
    entity_id = _resolve_related_entity(entity_type_enum, related_entity_public_id, requester) if entity_type_enum else None

    ticket = SupportTicket(
        ticket_number=_unique_ticket_number(),
        requester_id=requester.id,
        category=TicketCategory(category),
        priority=TicketPriority(priority) if priority else TicketPriority.NORMAL,
        status=TicketStatus.OPEN,
        subject=subject,
        related_entity_type=entity_type_enum,
        related_entity_id=entity_id,
    )
    db.session.add(ticket)
    db.session.flush()
    db.session.add(SupportMessage(ticket_id=ticket.id, sender_id=requester.id, body=initial_message, visibility=MessageVisibility.PUBLIC))
    db.session.commit()
    return ticket


def get_ticket_for_requester_or_404(user: User, ticket_public_id: str) -> SupportTicket:
    ticket = SupportTicket.query.filter_by(public_id=ticket_public_id, requester_id=user.id).first()
    if ticket is None:
        raise NotFoundError("Support ticket not found.")
    return ticket


def get_any_ticket_or_404(ticket_public_id: str) -> SupportTicket:
    ticket = SupportTicket.query.filter_by(public_id=ticket_public_id).first()
    if ticket is None:
        raise NotFoundError("Support ticket not found.")
    return ticket


def get_ticket_for_viewer_or_404(user: User, ticket_public_id: str) -> SupportTicket:
    if _is_staff_viewer(user):
        return get_any_ticket_or_404(ticket_public_id)
    return get_ticket_for_requester_or_404(user, ticket_public_id)


def list_tickets_for_requester(user: User, status: str | None = None, page: int = 1, per_page: int = 20):
    query = SupportTicket.query.filter_by(requester_id=user.id)
    if status:
        query = query.filter(SupportTicket.status == status)
    return query.order_by(SupportTicket.created_at.desc()).paginate(
        page=max(page, 1), per_page=max(min(per_page, 100), 1), error_out=False
    )


def list_tickets_for_agents(status: str | None = None, category: str | None = None, priority: str | None = None,
                             assigned_agent_public_id: str | None = None, unassigned_only: bool = False,
                             page: int = 1, per_page: int = 20):
    query = SupportTicket.query
    if status:
        query = query.filter(SupportTicket.status == status)
    if category:
        query = query.filter(SupportTicket.category == category)
    if priority:
        query = query.filter(SupportTicket.priority == priority)
    if unassigned_only:
        query = query.filter(SupportTicket.assigned_agent_id.is_(None))
    elif assigned_agent_public_id:
        agent = User.query.filter_by(public_id=assigned_agent_public_id).first()
        query = query.filter(SupportTicket.assigned_agent_id == (agent.id if agent else -1))
    return query.order_by(SupportTicket.priority.desc(), SupportTicket.created_at.asc()).paginate(
        page=max(page, 1), per_page=max(min(per_page, 100), 1), error_out=False
    )


def assign_ticket(actor: User, ticket: SupportTicket, agent_public_id: str | None) -> SupportTicket:
    if agent_public_id is None:
        ticket.assigned_agent_id = None
    else:
        agent = User.query.filter_by(public_id=agent_public_id, role=UserRole.ADMIN).first()
        if agent is None:
            raise NotFoundError("Agent not found.")
        ticket.assigned_agent_id = agent.id
        if ticket.status == TicketStatus.OPEN:
            ticket.status = TicketStatus.IN_PROGRESS
    db.session.commit()

    from app.audit.service import record

    record(actor, "SUPPORT_TICKET_ASSIGNED", entity_type="SUPPORT_TICKET", entity_id=ticket.public_id,
           after={"assigned_agent": agent_public_id})
    return ticket


def update_status(actor: User, ticket: SupportTicket, status: str, resolution_summary: str | None = None) -> SupportTicket:
    from app.models.base import _utcnow

    before_status = ticket.status.value
    new_status = TicketStatus(status)
    ticket.status = new_status
    if resolution_summary is not None:
        ticket.resolution_summary = resolution_summary
    if new_status == TicketStatus.RESOLVED:
        ticket.resolved_at = _utcnow()
    if new_status == TicketStatus.CLOSED:
        ticket.closed_at = _utcnow()
    db.session.commit()

    from app.audit.service import record

    record(actor, "SUPPORT_TICKET_STATUS_CHANGED", entity_type="SUPPORT_TICKET", entity_id=ticket.public_id,
           before={"status": before_status}, after={"status": new_status.value})

    if new_status in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
        from app.notifications.events import notify
        from app.models.notification import NotificationCategory

        notify(
            ticket.requester, NotificationCategory.SUPPORT,
            title=f"Ticket {ticket.ticket_number} {new_status.value.lower()}",
            body=resolution_summary or f"Your support ticket has been {new_status.value.lower()}.",
            entity_type="SUPPORT_TICKET", entity_id=ticket.public_id,
        )
    return ticket


# --- Messages ----------------------------------------------------------

def add_requester_message(user: User, ticket: SupportTicket, body: str) -> SupportMessage:
    if ticket.requester_id != user.id:
        raise AuthorizationError("You can only reply to your own tickets.")
    if ticket.status == TicketStatus.CLOSED:
        raise ValidationAppError("This ticket is closed.", code="TICKET_CLOSED")
    message = SupportMessage(ticket_id=ticket.id, sender_id=user.id, body=body, visibility=MessageVisibility.PUBLIC)
    db.session.add(message)
    if ticket.status == TicketStatus.WAITING_FOR_CUSTOMER:
        ticket.status = TicketStatus.IN_PROGRESS
    db.session.commit()
    return message


def add_staff_message(actor: User, ticket: SupportTicket, body: str, visibility: str = "PUBLIC") -> SupportMessage:
    if not _is_staff_viewer(actor):
        raise AuthorizationError()
    visibility_enum = MessageVisibility(visibility)
    if visibility_enum == MessageVisibility.INTERNAL and not _is_staff_manager(actor):
        raise AuthorizationError("Only staff with support-management permission can post internal notes.")
    if not _is_staff_manager(actor):
        raise AuthorizationError("Only staff with support-management permission can reply.")

    message = SupportMessage(ticket_id=ticket.id, sender_id=actor.id, body=body, visibility=visibility_enum)
    db.session.add(message)
    if ticket.status == TicketStatus.OPEN and visibility_enum == MessageVisibility.PUBLIC:
        ticket.status = TicketStatus.IN_PROGRESS
    db.session.commit()

    if visibility_enum == MessageVisibility.PUBLIC:
        from app.notifications.events import notify
        from app.models.notification import NotificationCategory

        notify(
            ticket.requester, NotificationCategory.SUPPORT,
            title=f"New reply on ticket {ticket.ticket_number}",
            body=body[:200], entity_type="SUPPORT_TICKET", entity_id=ticket.public_id,
        )
    return message


def list_messages_for_viewer(ticket: SupportTicket, viewer: User) -> list[SupportMessage]:
    if _is_staff_viewer(viewer):
        return ticket.messages.all()
    return ticket.messages.filter_by(visibility=MessageVisibility.PUBLIC).all()


# --- Attachments -----------------------------------------------------------

def add_attachment(actor: User, ticket: SupportTicket, filename: str, reference: str,
                    content_type: str | None = None, message_public_id: str | None = None) -> SupportAttachment:
    is_owner = ticket.requester_id == actor.id
    if not is_owner and not _is_staff_viewer(actor):
        raise AuthorizationError()

    message = None
    if message_public_id:
        message = ticket.messages.filter_by(public_id=message_public_id).first()
        if message is None:
            raise NotFoundError("Message not found on this ticket.")

    attachment = SupportAttachment(
        ticket_id=ticket.id, message_id=message.id if message else None, uploader_id=actor.id,
        filename=filename, reference=reference, content_type=content_type,
    )
    db.session.add(attachment)
    db.session.commit()
    return attachment


def list_attachments_for_viewer(ticket: SupportTicket, viewer: User) -> list[SupportAttachment]:
    is_staff = _is_staff_viewer(viewer)
    attachments = ticket.attachments.all()
    if is_staff:
        return attachments
    return [
        a for a in attachments
        if a.message is None or a.message.visibility == MessageVisibility.PUBLIC
    ]


def get_attachment_for_viewer_or_404(ticket: SupportTicket, viewer: User, attachment_public_id: str) -> SupportAttachment:
    attachment = ticket.attachments.filter_by(public_id=attachment_public_id).first()
    if attachment is None:
        raise NotFoundError("Attachment not found.")
    if not _is_staff_viewer(viewer):
        if ticket.requester_id != viewer.id:
            raise AuthorizationError()
        if attachment.message is not None and attachment.message.visibility != MessageVisibility.PUBLIC:
            raise AuthorizationError()
    return attachment
