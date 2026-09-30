"""Agent/admin support workspace (SRS 5: agent queues/assignment, SRS 7:
admin support management)."""
from flask import Blueprint, request

from app.auth.decorators import require_admin_permission, current_user
from app.common.responses import success
from app.support import service as support_service
from app.support.schemas import StaffMessageCreateSchema, AssignTicketSchema, TicketStatusUpdateSchema, AttachmentCreateSchema

admin_support_bp = Blueprint("admin_support", __name__, url_prefix="/api/v1/admin/support")


def _pagination(pagination):
    return {
        "page": pagination.page, "per_page": pagination.per_page,
        "total": pagination.total, "total_pages": pagination.pages,
    }


@admin_support_bp.route("/tickets", methods=["GET"])
@require_admin_permission("support.view", "support.manage")
def list_tickets():
    pagination = support_service.list_tickets_for_agents(
        status=request.args.get("status"),
        category=request.args.get("category"),
        priority=request.args.get("priority"),
        assigned_agent_public_id=request.args.get("agent_id"),
        unassigned_only=request.args.get("unassigned") == "true",
        page=request.args.get("page", default=1, type=int),
        per_page=request.args.get("per_page", default=20, type=int),
    )
    return success({"tickets": [t.to_public_dict() for t in pagination.items], "pagination": _pagination(pagination)})


@admin_support_bp.route("/tickets/<ticket_public_id>", methods=["GET"])
@require_admin_permission("support.view", "support.manage")
def get_ticket(ticket_public_id):
    user = current_user()
    ticket = support_service.get_any_ticket_or_404(ticket_public_id)
    data = ticket.to_public_dict()
    data["messages"] = [m.to_public_dict() for m in support_service.list_messages_for_viewer(ticket, user)]
    data["attachments"] = [a.to_public_dict() for a in support_service.list_attachments_for_viewer(ticket, user)]
    return success({"ticket": data})


@admin_support_bp.route("/tickets/<ticket_public_id>/assign", methods=["POST"])
@require_admin_permission("support.manage")
def assign_ticket(ticket_public_id):
    data = AssignTicketSchema().load(request.get_json(silent=True) or {})
    actor = current_user()
    ticket = support_service.get_any_ticket_or_404(ticket_public_id)
    ticket = support_service.assign_ticket(actor, ticket, data.get("agent_id"))
    return success({"ticket": ticket.to_public_dict()}, message="Ticket assignment updated.")


@admin_support_bp.route("/tickets/<ticket_public_id>/messages", methods=["POST"])
@require_admin_permission("support.view", "support.manage")
def add_message(ticket_public_id):
    data = StaffMessageCreateSchema().load(request.get_json(silent=True) or {})
    actor = current_user()
    ticket = support_service.get_any_ticket_or_404(ticket_public_id)
    message = support_service.add_staff_message(actor, ticket, data["body"], visibility=data["visibility"])
    return success({"message": message.to_public_dict()}, message="Message sent.", status_code=201)


@admin_support_bp.route("/tickets/<ticket_public_id>/attachments", methods=["POST"])
@require_admin_permission("support.view", "support.manage")
def add_attachment(ticket_public_id):
    data = AttachmentCreateSchema().load(request.get_json(silent=True) or {})
    actor = current_user()
    ticket = support_service.get_any_ticket_or_404(ticket_public_id)
    attachment = support_service.add_attachment(
        actor, ticket, data["filename"], data["reference"],
        content_type=data.get("content_type"), message_public_id=data.get("message_id"),
    )
    return success({"attachment": attachment.to_public_dict()}, message="Attachment added.", status_code=201)


@admin_support_bp.route("/tickets/<ticket_public_id>/status", methods=["PATCH"])
@require_admin_permission("support.manage")
def update_status(ticket_public_id):
    data = TicketStatusUpdateSchema().load(request.get_json(silent=True) or {})
    actor = current_user()
    ticket = support_service.get_any_ticket_or_404(ticket_public_id)
    ticket = support_service.update_status(actor, ticket, data["status"], resolution_summary=data.get("resolution_summary"))
    return success({"ticket": ticket.to_public_dict()}, message="Ticket status updated.")
