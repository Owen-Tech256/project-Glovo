"""Agent/admin dispute investigation and resolution workspace (SRS 6)."""
from flask import Blueprint, request

from app.auth.decorators import require_admin_permission, current_user
from app.common.responses import success
from app.disputes import service as dispute_service
from app.disputes.schemas import (
    EvidenceCreateSchema, DisputeStatusUpdateSchema, DisputePrioritySchema,
    DisputeActionCreateSchema, DisputeRefundResolveSchema,
)

admin_disputes_bp = Blueprint("admin_disputes", __name__, url_prefix="/api/v1/admin/disputes")


def _pagination(pagination):
    return {
        "page": pagination.page, "per_page": pagination.per_page,
        "total": pagination.total, "total_pages": pagination.pages,
    }


def _with_evidence(dispute):
    data = dispute.to_public_dict()
    data["evidence"] = [e.to_public_dict() for e in dispute.evidence.all()]
    data["actions"] = [a.to_public_dict() for a in dispute.actions.all()]
    return data


@admin_disputes_bp.route("", methods=["GET"])
@require_admin_permission("disputes.view", "disputes.manage", "disputes.financial_action")
def list_disputes():
    pagination = dispute_service.list_all_disputes(
        status=request.args.get("status"), category=request.args.get("category"),
        priority=request.args.get("priority"),
        page=request.args.get("page", default=1, type=int),
        per_page=request.args.get("per_page", default=20, type=int),
    )
    return success({"disputes": [d.to_public_dict() for d in pagination.items], "pagination": _pagination(pagination)})


@admin_disputes_bp.route("/<dispute_public_id>", methods=["GET"])
@require_admin_permission("disputes.view", "disputes.manage", "disputes.financial_action")
def get_dispute(dispute_public_id):
    dispute = dispute_service.get_any_dispute_or_404(dispute_public_id)
    return success({"dispute": _with_evidence(dispute)})


@admin_disputes_bp.route("/<dispute_public_id>/evidence", methods=["POST"])
@require_admin_permission("disputes.manage")
def add_evidence(dispute_public_id):
    data = EvidenceCreateSchema().load(request.get_json(silent=True) or {})
    actor = current_user()
    dispute = dispute_service.get_any_dispute_or_404(dispute_public_id)
    evidence = dispute_service.add_evidence(
        actor, dispute, data["evidence_type"], secure_reference=data.get("secure_reference"),
        description=data.get("description"),
    )
    return success({"evidence": evidence.to_public_dict()}, message="Evidence added.", status_code=201)


@admin_disputes_bp.route("/<dispute_public_id>/priority", methods=["PATCH"])
@require_admin_permission("disputes.manage")
def update_priority(dispute_public_id):
    data = DisputePrioritySchema().load(request.get_json(silent=True) or {})
    from app.extensions import db
    from app.models.dispute import DisputePriority

    dispute = dispute_service.get_any_dispute_or_404(dispute_public_id)
    dispute.priority = DisputePriority(data["priority"])
    db.session.commit()
    return success({"dispute": dispute.to_public_dict()}, message="Dispute priority updated.")


@admin_disputes_bp.route("/<dispute_public_id>/actions", methods=["POST"])
@require_admin_permission("disputes.manage")
def record_action(dispute_public_id):
    data = DisputeActionCreateSchema().load(request.get_json(silent=True) or {})
    actor = current_user()
    dispute = dispute_service.get_any_dispute_or_404(dispute_public_id)
    action = dispute_service.record_action(actor, dispute, data["action_type"], reason=data.get("reason"))
    return success({"action": action.to_public_dict()}, message="Action recorded.", status_code=201)


@admin_disputes_bp.route("/<dispute_public_id>/resolve", methods=["POST"])
@require_admin_permission("disputes.manage")
def resolve_dispute(dispute_public_id):
    data = DisputeStatusUpdateSchema().load(request.get_json(silent=True) or {})
    actor = current_user()
    dispute = dispute_service.get_any_dispute_or_404(dispute_public_id)
    dispute = dispute_service.update_status(actor, dispute, data["status"], resolution=data.get("resolution"))
    return success({"dispute": dispute.to_public_dict()}, message="Dispute status updated.")


@admin_disputes_bp.route("/<dispute_public_id>/resolve-with-refund", methods=["POST"])
@require_admin_permission("disputes.financial_action")
def resolve_with_refund(dispute_public_id):
    data = DisputeRefundResolveSchema().load(request.get_json(silent=True) or {})
    actor = current_user()
    dispute = dispute_service.get_any_dispute_or_404(dispute_public_id)
    action = dispute_service.resolve_with_refund(actor, dispute, data.get("amount"), data["reason"])
    dispute = dispute_service.update_status(actor, dispute, "RESOLVED", resolution=data["reason"])
    return success(
        {"dispute": dispute.to_public_dict(), "action": action.to_public_dict()},
        message="Dispute resolved with refund.",
    )
