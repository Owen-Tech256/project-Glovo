"""Analytics dashboards (SRS 9, API section 13). All read-only; every
number is computed live from Phase 1-6 authoritative tables - see
app/analytics/service.py's module docstring."""
from flask import Blueprint, request

from app.auth.decorators import require_admin_permission
from app.common.responses import success
from app.analytics import service as analytics_service

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/v1/analytics")

_VIEW_PERMS = ("analytics.view",)


def _dates():
    return request.args.get("date_from"), request.args.get("date_to")


@analytics_bp.route("/overview", methods=["GET"])
@require_admin_permission(*_VIEW_PERMS)
def overview():
    date_from, date_to = _dates()
    return success(analytics_service.overview(date_from, date_to))


@analytics_bp.route("/orders", methods=["GET"])
@require_admin_permission(*_VIEW_PERMS)
def orders():
    date_from, date_to = _dates()
    return success(analytics_service.orders_metrics(date_from, date_to, branch_public_id=request.args.get("branch_id")))


@analytics_bp.route("/finance", methods=["GET"])
@require_admin_permission("finance.view")
def finance():
    date_from, date_to = _dates()
    return success(analytics_service.finance_metrics(date_from, date_to))


@analytics_bp.route("/vendors", methods=["GET"])
@require_admin_permission(*_VIEW_PERMS)
def vendors():
    date_from, date_to = _dates()
    return success(analytics_service.vendor_metrics(date_from, date_to, vendor_public_id=request.args.get("vendor_id")))


@analytics_bp.route("/riders", methods=["GET"])
@require_admin_permission(*_VIEW_PERMS)
def riders():
    date_from, date_to = _dates()
    return success(analytics_service.rider_metrics(date_from, date_to, rider_public_id=request.args.get("rider_id")))


@analytics_bp.route("/delivery", methods=["GET"])
@require_admin_permission(*_VIEW_PERMS)
def delivery():
    date_from, date_to = _dates()
    return success(analytics_service.delivery_metrics(date_from, date_to))


@analytics_bp.route("/customers", methods=["GET"])
@require_admin_permission(*_VIEW_PERMS)
def customers():
    date_from, date_to = _dates()
    return success(analytics_service.customer_metrics(date_from, date_to))


@analytics_bp.route("/promotions-ads", methods=["GET"])
@require_admin_permission(*_VIEW_PERMS)
def promotions_ads():
    date_from, date_to = _dates()
    return success(analytics_service.promotion_ad_metrics(date_from, date_to))


@analytics_bp.route("/support-disputes", methods=["GET"])
@require_admin_permission("analytics.view", "support.view", "disputes.view")
def support_disputes():
    date_from, date_to = _dates()
    return success(analytics_service.support_dispute_metrics(date_from, date_to))
