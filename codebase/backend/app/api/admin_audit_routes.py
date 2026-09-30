"""Read-only audit trail views (SRS 10: "Protect audit records from
ordinary alteration/deletion" - accordingly, there is no write/edit/delete
endpoint here at all, only listing/lookup)."""
from flask import Blueprint, request

from app.auth.decorators import require_admin_permission
from app.common.responses import success
from app.audit import service as audit_service

admin_audit_bp = Blueprint("admin_audit", __name__, url_prefix="/api/v1/admin/audit")


@admin_audit_bp.route("/events", methods=["GET"])
@require_admin_permission("audit.view")
def list_events():
    pagination = audit_service.list_events(
        entity_type=request.args.get("entity_type"), entity_id=request.args.get("entity_id"),
        user_public_id=request.args.get("user_id"), action=request.args.get("action"),
        page=request.args.get("page", default=1, type=int), per_page=request.args.get("per_page", default=20, type=int),
    )
    return success({
        "events": [e.to_public_dict() for e in pagination.items],
        "pagination": {
            "page": pagination.page, "per_page": pagination.per_page,
            "total": pagination.total, "total_pages": pagination.pages,
        },
    })
