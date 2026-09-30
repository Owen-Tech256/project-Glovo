"""Customer/vendor/rider-facing support endpoints - creating and viewing
one's own tickets. Agent/admin views live in
app/api/admin_support_routes.py."""
from flask import Blueprint, request

from app.auth.decorators import require_role, current_user
from app.common.responses import success
from app.models.user import UserRole
from app.support import service as support_service
from app.support.schemas import TicketCreateSchema, MessageCreateSchema, AttachmentCreateSchema

support_bp = Blueprint("support", __name__, url_prefix="/api/v1/support")

_REQUESTER_ROLES = (UserRole.CUSTOMER.value, UserRole.VENDOR.value, UserRole.RIDER.value)


def _pagination(pagination):
    return {
        "page": pagination.page, "per_page": pagination.per_page,
        "total": pagination.total, "total_pages": pagination.pages,
    }


@support_bp.route("/tickets", methods=["POST"])
@require_role(*_REQUESTER_ROLES)
def create_ticket():
    data = TicketCreateSchema().load(request.get_json(silent=True) or {})
    user = current_user()
    ticket = support_service.create_ticket(
        user, data["category"], data["subject"], data["message"],
        priority=data.get("priority"), related_entity_type=data.get("related_entity_type"),
        related_entity_public_id=data.get("related_entity_id"),
    )
    return success({"ticket": ticket.to_public_dict()}, message="Support ticket created.", status_code=201)


@support_bp.route("/tickets", methods=["GET"])
@require_role(*_REQUESTER_ROLES)
def list_my_tickets():
    user = current_user()
    status = request.args.get("status")
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=20, type=int)
    pagination = support_service.list_tickets_for_requester(user, status=status, page=page, per_page=per_page)
    return success({"tickets": [t.to_public_dict() for t in pagination.items], "pagination": _pagination(pagination)})


@support_bp.route("/tickets/<ticket_public_id>", methods=["GET"])
@require_role(*_REQUESTER_ROLES)
def get_ticket(ticket_public_id):
    user = current_user()
    ticket = support_service.get_ticket_for_requester_or_404(user, ticket_public_id)
    data = ticket.to_public_dict()
    data["messages"] = [m.to_public_dict() for m in support_service.list_messages_for_viewer(ticket, user)]
    data["attachments"] = [a.to_public_dict() for a in support_service.list_attachments_for_viewer(ticket, user)]
    return success({"ticket": data})


@support_bp.route("/tickets/<ticket_public_id>/messages", methods=["POST"])
@require_role(*_REQUESTER_ROLES)
def add_message(ticket_public_id):
    data = MessageCreateSchema().load(request.get_json(silent=True) or {})
    user = current_user()
    ticket = support_service.get_ticket_for_requester_or_404(user, ticket_public_id)
    message = support_service.add_requester_message(user, ticket, data["body"])
    return success({"message": message.to_public_dict()}, message="Message sent.", status_code=201)


@support_bp.route("/tickets/<ticket_public_id>/attachments", methods=["POST"])
@require_role(*_REQUESTER_ROLES)
def add_attachment(ticket_public_id):
    data = AttachmentCreateSchema().load(request.get_json(silent=True) or {})
    user = current_user()
    ticket = support_service.get_ticket_for_requester_or_404(user, ticket_public_id)
    attachment = support_service.add_attachment(
        user, ticket, data["filename"], data["reference"],
        content_type=data.get("content_type"), message_public_id=data.get("message_id"),
    )
    return success({"attachment": attachment.to_public_dict()}, message="Attachment added.", status_code=201)
