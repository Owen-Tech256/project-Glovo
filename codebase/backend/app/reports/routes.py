"""Report definitions and exports (SRS 9/12/13). Every route requires
`reports.manage` - a SUPER_ADMIN or ANALYST-equivalent capability; there
is no per-requester ownership restriction on exports since these are
organization-wide operational reports, not personal data."""
import os

from flask import Blueprint, request, send_file

from app.auth.decorators import require_admin_permission, current_user
from app.common.responses import success
from app.reports import service as report_service
from app.reports.schemas import ReportDefinitionCreateSchema, ReportExportCreateSchema

reports_bp = Blueprint("reports", __name__, url_prefix="/api/v1/reports")


@reports_bp.route("", methods=["GET"])
@require_admin_permission("reports.manage")
def list_definitions():
    return success({"report_definitions": [d.to_public_dict() for d in report_service.list_definitions()]})


@reports_bp.route("", methods=["POST"])
@require_admin_permission("reports.manage")
def create_definition():
    data = ReportDefinitionCreateSchema().load(request.get_json(silent=True) or {})
    actor = current_user()
    definition = report_service.create_definition(
        actor, data["name"], data["report_type"], data.get("configuration") or {}, data.get("access_level", "analytics.view")
    )
    return success({"report_definition": definition.to_public_dict()}, message="Report definition created.", status_code=201)


@reports_bp.route("/exports", methods=["GET"])
@require_admin_permission("reports.manage")
def list_exports():
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=20, type=int)
    pagination = report_service.list_exports(page=page, per_page=per_page)
    return success({
        "exports": [e.to_public_dict() for e in pagination.items],
        "pagination": {
            "page": pagination.page, "per_page": pagination.per_page,
            "total": pagination.total, "total_pages": pagination.pages,
        },
    })


@reports_bp.route("/exports", methods=["POST"])
@require_admin_permission("reports.manage")
def request_export():
    data = ReportExportCreateSchema().load(request.get_json(silent=True) or {})
    actor = current_user()
    export = report_service.request_export(
        actor, data.get("report_type"), data.get("report_definition_id"),
        data.get("date_from"), data.get("date_to"), data.get("filters") or {},
    )
    return success({"export": export.to_public_dict()}, message="Report export generated.", status_code=201)


@reports_bp.route("/exports/<export_public_id>", methods=["GET"])
@require_admin_permission("reports.manage")
def get_export(export_public_id):
    export = report_service.get_export_or_404(export_public_id)
    return success({"export": export.to_public_dict()})


@reports_bp.route("/exports/<export_public_id>/download", methods=["GET"])
@require_admin_permission("reports.manage")
def download_export(export_public_id):
    export = report_service.get_export_or_404(export_public_id)
    path = report_service.export_file_path(export)
    return send_file(path, mimetype="text/csv", as_attachment=True,
                      download_name=f"{export.report_type.lower()}-{export.public_id[:8]}.csv")
