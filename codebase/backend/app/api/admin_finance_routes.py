from flask import Blueprint, request

from app.auth.decorators import require_role, current_user
from app.common.responses import success
from app.payments import admin_finance_service, payment_service, refund_service, vendor_finance_service
from app.payments.schemas import (
    CommissionRuleCreateSchema, CommissionRuleUpdateSchema, WalletAdjustmentSchema, RefundRejectSchema,
)

admin_finance_bp = Blueprint("admin_finance", __name__, url_prefix="/api/v1/admin")


def _pagination(pagination):
    return {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "total_pages": pagination.pages,
    }


# --- Payments ------------------------------------------------------------

@admin_finance_bp.route("/payments", methods=["GET"])
@require_role("ADMIN")
def list_payments():
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=20, type=int)
    status = request.args.get("status")
    pagination = payment_service.list_all_payments(status=status, page=page, per_page=per_page)
    return success({"payments": [p.to_public_dict() for p in pagination.items], "pagination": _pagination(pagination)})


# --- Refunds ---------------------------------------------------------------

@admin_finance_bp.route("/refunds", methods=["GET"])
@require_role("ADMIN")
def list_refunds():
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=20, type=int)
    status = request.args.get("status")
    pagination = refund_service.list_all_refunds(status=status, page=page, per_page=per_page)
    return success({"refunds": [r.to_public_dict() for r in pagination.items], "pagination": _pagination(pagination)})


@admin_finance_bp.route("/refunds/<refund_public_id>/approve", methods=["POST"])
@require_role("ADMIN")
def approve_refund(refund_public_id):
    admin = current_user()
    refund = admin_finance_service.approve_refund(admin, refund_public_id, request.remote_addr)
    return success({"refund": refund.to_public_dict()}, message="Refund approved and processed.")


@admin_finance_bp.route("/refunds/<refund_public_id>/reject", methods=["POST"])
@require_role("ADMIN")
def reject_refund(refund_public_id):
    data = RefundRejectSchema().load(request.get_json(silent=True) or {})
    admin = current_user()
    refund = admin_finance_service.reject_refund(admin, refund_public_id, data.get("reason"), request.remote_addr)
    return success({"refund": refund.to_public_dict()}, message="Refund rejected.")


@admin_finance_bp.route("/refunds/<refund_public_id>/retry", methods=["POST"])
@require_role("ADMIN")
def retry_refund(refund_public_id):
    admin = current_user()
    refund = admin_finance_service.retry_refund(admin, refund_public_id, request.remote_addr)
    return success({"refund": refund.to_public_dict()}, message="Refund retried.")


# --- Payouts -----------------------------------------------------------

@admin_finance_bp.route("/payouts", methods=["GET"])
@require_role("ADMIN")
def list_payouts():
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=20, type=int)
    status = request.args.get("status")
    pagination = vendor_finance_service.list_all_payouts(status=status, page=page, per_page=per_page)
    return success({"payouts": [p.to_public_dict() for p in pagination.items], "pagination": _pagination(pagination)})


@admin_finance_bp.route("/payouts/<payout_public_id>/retry", methods=["POST"])
@require_role("ADMIN")
def retry_payout(payout_public_id):
    admin = current_user()
    payout = admin_finance_service.retry_payout(admin, payout_public_id, request.remote_addr)
    return success({"payout": payout.to_public_dict()}, message="Payout retried.")


# --- Commission rules ------------------------------------------------------

@admin_finance_bp.route("/commission-rules", methods=["GET"])
@require_role("ADMIN")
def list_commission_rules():
    status = request.args.get("status")
    rules = admin_finance_service.list_commission_rules(status=status)
    return success({"commission_rules": [r.to_public_dict() for r in rules]})


@admin_finance_bp.route("/commission-rules", methods=["POST"])
@require_role("ADMIN")
def create_commission_rule():
    data = CommissionRuleCreateSchema().load(request.get_json(silent=True) or {})
    admin = current_user()
    rule = admin_finance_service.create_commission_rule(admin, data, request.remote_addr)
    return success({"commission_rule": rule.to_public_dict()}, message="Commission rule created.", status_code=201)


@admin_finance_bp.route("/commission-rules/<rule_public_id>", methods=["PATCH"])
@require_role("ADMIN")
def update_commission_rule(rule_public_id):
    data = CommissionRuleUpdateSchema().load(request.get_json(silent=True) or {})
    admin = current_user()
    rule = admin_finance_service.get_commission_rule_or_404(rule_public_id)
    rule = admin_finance_service.update_commission_rule(admin, rule, data, request.remote_addr)
    return success({"commission_rule": rule.to_public_dict()}, message="Commission rule updated.")


# --- Wallet adjustments ------------------------------------------------

@admin_finance_bp.route("/wallet-adjustments", methods=["POST"])
@require_role("ADMIN")
def create_wallet_adjustment():
    data = WalletAdjustmentSchema().load(request.get_json(silent=True) or {})
    admin = current_user()
    entry = admin_finance_service.create_wallet_adjustment(
        admin, data["rider_id"], data["amount"], data["reason"], request.remote_addr
    )
    return success({"wallet_transaction": entry.to_public_dict()}, message="Wallet adjustment applied.", status_code=201)


# --- Reconciliation ------------------------------------------------------

@admin_finance_bp.route("/reconciliation/summary", methods=["GET"])
@require_role("ADMIN")
def reconciliation_summary():
    return success(admin_finance_service.reconciliation_summary())
