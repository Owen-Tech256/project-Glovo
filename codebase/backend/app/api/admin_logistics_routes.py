from flask import Blueprint, request

from app.auth.decorators import require_role, current_user
from app.common.responses import success
from app.logistics import admin_service
from app.logistics.schemas import AdminRiderStatusUpdateSchema, AdminDocumentReviewSchema, AdminReassignSchema

admin_logistics_bp = Blueprint("admin_logistics", __name__, url_prefix="/api/v1/admin")


@admin_logistics_bp.route("/riders", methods=["GET"])
@require_role("ADMIN")
def list_riders():
    status = request.args.get("status")
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=20, type=int)
    pagination = admin_service.list_riders(onboarding_status=status, page=page, per_page=per_page)
    return success({
        "riders": [r.to_public_dict() for r in pagination.items],
        "pagination": {
            "page": pagination.page, "per_page": pagination.per_page,
            "total": pagination.total, "total_pages": pagination.pages,
        },
    })


@admin_logistics_bp.route("/riders/<rider_id>", methods=["GET"])
@require_role("ADMIN")
def get_rider(rider_id):
    rider = admin_service.get_rider_or_404(rider_id)
    data = rider.to_public_dict()
    data["documents"] = [d.to_public_dict() for d in rider.documents.all()]
    return success({"rider": data})


@admin_logistics_bp.route("/riders/<rider_id>/status", methods=["PATCH"])
@require_role("ADMIN")
def update_rider_status(rider_id):
    data = AdminRiderStatusUpdateSchema().load(request.get_json(silent=True) or {})
    rider = admin_service.set_onboarding_status(
        current_user(), rider_id, data["status"], data.get("reason"), request.remote_addr
    )
    return success({"rider": rider.to_public_dict()}, message="Rider status updated.")


@admin_logistics_bp.route("/riders/<rider_id>/documents", methods=["GET"])
@require_role("ADMIN")
def list_rider_documents(rider_id):
    documents = admin_service.list_rider_documents(rider_id)
    return success({"documents": [d.to_public_dict() for d in documents]})


@admin_logistics_bp.route("/riders/<rider_id>/documents/<document_id>", methods=["PATCH"])
@require_role("ADMIN")
def review_document(rider_id, document_id):
    data = AdminDocumentReviewSchema().load(request.get_json(silent=True) or {})
    document = admin_service.review_document(
        current_user(), rider_id, document_id, data["verification_status"], data.get("review_notes"),
        request.remote_addr,
    )
    return success({"document": document.to_public_dict()}, message="Document reviewed.")


@admin_logistics_bp.route("/logistics/dispatch-health", methods=["GET"])
@require_role("ADMIN")
def dispatch_health():
    return success({"dispatch_health": admin_service.get_dispatch_health()})


@admin_logistics_bp.route("/deliveries", methods=["GET"])
@require_role("ADMIN")
def list_deliveries():
    status = request.args.get("status")
    branch_id = request.args.get("branch_id")
    rider_id = request.args.get("rider_id")
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=20, type=int)
    pagination = admin_service.list_deliveries(
        status=status, branch_public_id=branch_id, rider_public_id=rider_id, page=page, per_page=per_page
    )
    return success({
        "deliveries": [d.to_public_dict() for d in pagination.items],
        "pagination": {
            "page": pagination.page, "per_page": pagination.per_page,
            "total": pagination.total, "total_pages": pagination.pages,
        },
    })


@admin_logistics_bp.route("/deliveries/<delivery_id>", methods=["GET"])
@require_role("ADMIN")
def get_delivery(delivery_id):
    delivery = admin_service.get_delivery_or_404(delivery_id)
    data = delivery.to_public_dict()
    data["status_history"] = [h.to_public_dict() for h in admin_service.get_delivery_status_history(delivery)]
    return success({"delivery": data})


@admin_logistics_bp.route("/deliveries/<delivery_id>/reassign", methods=["POST"])
@require_role("ADMIN")
def reassign_delivery(delivery_id):
    data = AdminReassignSchema().load(request.get_json(silent=True) or {})
    delivery = admin_service.reassign_delivery(current_user(), delivery_id, data.get("reason"), request.remote_addr)
    return success({"delivery": delivery.to_public_dict()}, message="Delivery reassignment triggered.")
