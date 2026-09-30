"""
Admin surface for Phase 6 growth & engagement: promotions, ad campaigns,
review moderation, and notification templates - grouped in one file the
same way admin_finance_routes.py groups every Phase 5 admin concern,
rather than one file per sub-domain.
"""
from flask import Blueprint, request

from app.auth.decorators import require_role, current_user
from app.common.responses import success
from app.common.errors import NotFoundError

from app.promotions import service as promotion_service
from app.promotions.schemas import PromotionCreateSchema, PromotionUpdateSchema

from app.advertising import service as ad_service
from app.advertising.schemas import AdCampaignRejectSchema

from app.reviews import service as review_service
from app.reviews.schemas import ReviewModerateSchema, ReviewReportResolveSchema

from app.models.notification_template import NotificationTemplate, NotificationChannel, NotificationTemplateStatus
from app.extensions import db

admin_growth_bp = Blueprint("admin_growth", __name__, url_prefix="/api/v1/admin")

promotion_create_schema = PromotionCreateSchema()
promotion_update_schema = PromotionUpdateSchema()
ad_reject_schema = AdCampaignRejectSchema()
review_moderate_schema = ReviewModerateSchema()
report_resolve_schema = ReviewReportResolveSchema()


def _pagination(pagination):
    return {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "total_pages": pagination.pages,
    }


# --- Promotions --------------------------------------------------------

@admin_growth_bp.route("/promotions", methods=["GET"])
@require_role("ADMIN")
def list_promotions():
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=20, type=int)
    status = request.args.get("status")
    vendor_id = request.args.get("vendor_id")
    pagination = promotion_service.list_all_promotions(status=status, vendor_public_id=vendor_id, page=page, per_page=per_page)
    return success({"promotions": [p.to_public_dict(include_scopes=True) for p in pagination.items], "pagination": _pagination(pagination)})


@admin_growth_bp.route("/promotions", methods=["POST"])
@require_role("ADMIN")
def create_promotion():
    admin = current_user()
    data = promotion_create_schema.load(request.get_json(silent=True) or {})
    data["created_by_user_id"] = admin.id
    promotion = promotion_service.create_promotion(None, data)
    return success({"promotion": promotion.to_public_dict(include_scopes=True)}, message="Promotion created.", status_code=201)


@admin_growth_bp.route("/promotions/<promotion_public_id>", methods=["PATCH"])
@require_role("ADMIN")
def update_promotion(promotion_public_id):
    promotion = promotion_service.get_any_promotion_or_404(promotion_public_id)
    data = promotion_update_schema.load(request.get_json(silent=True) or {})
    promotion = promotion_service.update_promotion(promotion, data, vendor=promotion.vendor)
    return success({"promotion": promotion.to_public_dict(include_scopes=True)}, message="Promotion updated.")


# --- Ad campaigns --------------------------------------------------------

@admin_growth_bp.route("/ad-campaigns", methods=["GET"])
@require_role("ADMIN")
def list_ad_campaigns():
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=20, type=int)
    status = request.args.get("status")
    pagination = ad_service.list_all_campaigns(status=status, page=page, per_page=per_page)
    return success({"campaigns": [c.to_public_dict() for c in pagination.items], "pagination": _pagination(pagination)})


@admin_growth_bp.route("/ad-campaigns/<campaign_public_id>", methods=["GET"])
@require_role("ADMIN")
def get_ad_campaign(campaign_public_id):
    campaign = ad_service.get_any_campaign_or_404(campaign_public_id)
    data = campaign.to_public_dict()
    data["performance"] = ad_service.campaign_performance(campaign)
    return success({"campaign": data})


@admin_growth_bp.route("/ad-campaigns/<campaign_public_id>/approve", methods=["POST"])
@require_role("ADMIN")
def approve_ad_campaign(campaign_public_id):
    admin = current_user()
    campaign = ad_service.get_any_campaign_or_404(campaign_public_id)
    campaign = ad_service.admin_approve_campaign(campaign, admin)
    return success({"campaign": campaign.to_public_dict()}, message="Campaign approved.")


@admin_growth_bp.route("/ad-campaigns/<campaign_public_id>/reject", methods=["POST"])
@require_role("ADMIN")
def reject_ad_campaign(campaign_public_id):
    admin = current_user()
    campaign = ad_service.get_any_campaign_or_404(campaign_public_id)
    data = ad_reject_schema.load(request.get_json(silent=True) or {})
    campaign = ad_service.admin_reject_campaign(campaign, admin, data["reason"])
    return success({"campaign": campaign.to_public_dict()}, message="Campaign rejected.")


@admin_growth_bp.route("/ad-campaigns/<campaign_public_id>/pause", methods=["POST"])
@require_role("ADMIN")
def pause_ad_campaign(campaign_public_id):
    campaign = ad_service.get_any_campaign_or_404(campaign_public_id)
    campaign = ad_service.admin_pause_campaign(campaign)
    return success({"campaign": campaign.to_public_dict()}, message="Campaign paused.")


# --- Review moderation ---------------------------------------------------

@admin_growth_bp.route("/reviews", methods=["GET"])
@require_role("ADMIN")
def list_reviews():
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=20, type=int)
    status = request.args.get("status")
    pagination = review_service.list_all_reviews(status=status, page=page, per_page=per_page)
    return success({"reviews": [r.to_public_dict() for r in pagination.items], "pagination": _pagination(pagination)})


@admin_growth_bp.route("/reviews/<review_public_id>/moderate", methods=["PATCH"])
@require_role("ADMIN")
def moderate_review(review_public_id):
    review = review_service.get_review_or_404(review_public_id)
    data = review_moderate_schema.load(request.get_json(silent=True) or {})
    review = review_service.moderate_review(review, data["status"])
    return success({"review": review.to_public_dict()}, message="Review updated.")


@admin_growth_bp.route("/review-reports", methods=["GET"])
@require_role("ADMIN")
def list_review_reports():
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=20, type=int)
    status = request.args.get("status")
    pagination = review_service.list_all_reports(status=status, page=page, per_page=per_page)
    return success({"reports": [r.to_public_dict() for r in pagination.items], "pagination": _pagination(pagination)})


@admin_growth_bp.route("/review-reports/<report_public_id>", methods=["PATCH"])
@require_role("ADMIN")
def resolve_review_report(report_public_id):
    admin = current_user()
    report = review_service.get_report_or_404(report_public_id)
    data = report_resolve_schema.load(request.get_json(silent=True) or {})
    report = review_service.resolve_report(report, admin, data["status"])
    if data.get("hide_review"):
        review_service.moderate_review(report.review, "HIDDEN")
    return success({"report": report.to_public_dict()}, message="Report resolved.")


# --- Notification templates ---------------------------------------------

@admin_growth_bp.route("/notification-templates", methods=["GET"])
@require_role("ADMIN")
def list_notification_templates():
    templates = NotificationTemplate.query.order_by(NotificationTemplate.key, NotificationTemplate.channel).all()
    return success({"templates": [t.to_public_dict() for t in templates]})


@admin_growth_bp.route("/notification-templates", methods=["POST"])
@require_role("ADMIN")
def create_notification_template():
    payload = request.get_json(silent=True) or {}
    key = payload.get("key")
    channel = payload.get("channel")
    if not key or channel not in [c.value for c in NotificationChannel]:
        from app.common.errors import ValidationAppError

        raise ValidationAppError("key and a valid channel are required.", code="VALIDATION_ERROR")
    if NotificationTemplate.query.filter_by(key=key, channel=channel).first():
        from app.common.errors import ConflictError

        raise ConflictError("A template with this key and channel already exists.")
    template = NotificationTemplate(
        key=key, channel=NotificationChannel(channel), category=payload.get("category", "ACCOUNT"),
        title_template=payload.get("title_template", ""), body_template=payload.get("body_template", ""),
        status=NotificationTemplateStatus.ACTIVE,
    )
    db.session.add(template)
    db.session.commit()
    return success({"template": template.to_public_dict()}, message="Template created.", status_code=201)


@admin_growth_bp.route("/notification-templates/<template_public_id>", methods=["PATCH"])
@require_role("ADMIN")
def update_notification_template(template_public_id):
    template = NotificationTemplate.query.filter_by(public_id=template_public_id).first()
    if template is None:
        raise NotFoundError("Notification template not found.")
    payload = request.get_json(silent=True) or {}
    for field in ("title_template", "body_template", "category"):
        if field in payload:
            setattr(template, field, payload[field])
    if "status" in payload:
        template.status = NotificationTemplateStatus(payload["status"])
    template.version = (template.version or 1) + 1
    db.session.commit()
    return success({"template": template.to_public_dict()}, message="Template updated.")
