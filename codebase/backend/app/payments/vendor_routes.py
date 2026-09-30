from flask import Blueprint, request

from app.auth.decorators import require_role, current_user
from app.common.responses import success
from app.vendors.helpers import get_or_create_vendor
from app.payments import vendor_finance_service
from app.payments.schemas import PayoutRequestSchema

vendor_finance_bp = Blueprint("vendor_finance", __name__, url_prefix="/api/v1/vendor")


@vendor_finance_bp.route("/financial-summary", methods=["GET"])
@require_role("VENDOR")
def get_financial_summary():
    vendor = get_or_create_vendor(current_user())
    return success(vendor_finance_service.get_financial_summary(vendor))


@vendor_finance_bp.route("/payouts", methods=["GET"])
@require_role("VENDOR")
def list_payouts():
    vendor = get_or_create_vendor(current_user())
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=20, type=int)
    pagination = vendor_finance_service.list_vendor_payouts(vendor, page=page, per_page=per_page)
    return success(
        {
            "payouts": [p.to_public_dict() for p in pagination.items],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "total_pages": pagination.pages,
            },
        }
    )


@vendor_finance_bp.route("/payouts", methods=["POST"])
@require_role("VENDOR")
def create_payout():
    data = PayoutRequestSchema().load(request.get_json(silent=True) or {})
    vendor = get_or_create_vendor(current_user())
    payout, was_created = vendor_finance_service.request_payout(
        vendor, data.get("amount"), data["destination_reference"], data.get("idempotency_key")
    )
    message = "Payout requested." if was_created else "Payout already requested for this request."
    return success({"payout": payout.to_public_dict()}, message=message, status_code=201 if was_created else 200)


@vendor_finance_bp.route("/payouts/<payout_public_id>", methods=["GET"])
@require_role("VENDOR")
def get_payout(payout_public_id):
    vendor = get_or_create_vendor(current_user())
    payout = vendor_finance_service.get_owned_payout_or_404(vendor, payout_public_id)
    return success({"payout": payout.to_public_dict()})


@vendor_finance_bp.route("/payouts/<payout_public_id>/cancel", methods=["POST"])
@require_role("VENDOR")
def cancel_payout(payout_public_id):
    vendor = get_or_create_vendor(current_user())
    payout = vendor_finance_service.get_owned_payout_or_404(vendor, payout_public_id)
    payout = vendor_finance_service.cancel_payout(payout)
    return success({"payout": payout.to_public_dict()}, message="Payout cancelled.")
