"""Customer/vendor/rider-facing dispute endpoints - opening a dispute over
one's own order and tracking it. Agent/admin investigation and resolution
live in app/api/admin_dispute_routes.py."""
from flask import Blueprint, request

from app.auth.decorators import require_role, current_user
from app.common.responses import success
from app.models.user import UserRole
from app.disputes import service as dispute_service
from app.disputes.schemas import DisputeCreateSchema, EvidenceCreateSchema

disputes_bp = Blueprint("disputes", __name__, url_prefix="/api/v1/disputes")

_PARTY_ROLES = (UserRole.CUSTOMER.value, UserRole.VENDOR.value, UserRole.RIDER.value)


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


@disputes_bp.route("", methods=["POST"])
@require_role(*_PARTY_ROLES)
def create_dispute():
    data = DisputeCreateSchema().load(request.get_json(silent=True) or {})
    user = current_user()
    dispute = dispute_service.create_dispute(
        user, data["order_id"], data["category"], data["description"],
        delivery_public_id=data.get("delivery_id"), payment_public_id=data.get("payment_id"),
        refund_public_id=data.get("refund_id"), ticket_public_id=data.get("ticket_id"),
    )
    return success({"dispute": _with_evidence(dispute)}, message="Dispute opened.", status_code=201)


@disputes_bp.route("", methods=["GET"])
@require_role(*_PARTY_ROLES)
def list_my_disputes():
    user = current_user()
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=20, type=int)
    pagination = dispute_service.list_disputes_for_user(user, page=page, per_page=per_page)
    return success({"disputes": [d.to_public_dict() for d in pagination.items], "pagination": _pagination(pagination)})


@disputes_bp.route("/<dispute_public_id>", methods=["GET"])
@require_role(*_PARTY_ROLES)
def get_dispute(dispute_public_id):
    user = current_user()
    dispute = dispute_service.get_dispute_for_user_or_404(user, dispute_public_id)
    return success({"dispute": _with_evidence(dispute)})


@disputes_bp.route("/<dispute_public_id>/evidence", methods=["POST"])
@require_role(*_PARTY_ROLES)
def add_evidence(dispute_public_id):
    data = EvidenceCreateSchema().load(request.get_json(silent=True) or {})
    user = current_user()
    dispute = dispute_service.get_dispute_for_user_or_404(user, dispute_public_id)
    evidence = dispute_service.add_evidence(
        user, dispute, data["evidence_type"], secure_reference=data.get("secure_reference"),
        description=data.get("description"),
    )
    return success({"evidence": evidence.to_public_dict()}, message="Evidence submitted.", status_code=201)
