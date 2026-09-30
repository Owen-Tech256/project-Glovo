from flask import Blueprint, request

from app.common.responses import success
from app.auth.decorators import require_role, current_user
from app.models.user import UserRole
from app.orders import service as order_service
from app.reviews import service as review_service
from app.reviews.schemas import (
    ReviewCreateSchema, ReviewUpdateSchema, ReviewReportSchema, ReviewResponseSchema,
)

reviews_bp = Blueprint("reviews", __name__, url_prefix="/api/v1")

create_schema = ReviewCreateSchema()
update_schema = ReviewUpdateSchema()
report_schema = ReviewReportSchema()
response_schema = ReviewResponseSchema()


@reviews_bp.get("/orders/<order_public_id>/reviews")
@require_role(UserRole.CUSTOMER.value)
def list_order_reviewable(order_public_id):
    """Every target this order makes reviewable, each annotated with the
    customer's existing review of it (if any) - the shape the order-detail
    page renders its review forms from."""
    user = current_user()
    order = order_service.get_owned_order_or_404(user, order_public_id)
    return success({"reviewable": review_service.get_reviewable_targets(order, user)})


@reviews_bp.post("/orders/<order_public_id>/reviews")
@require_role(UserRole.CUSTOMER.value)
def create_order_review(order_public_id):
    user = current_user()
    order = order_service.get_owned_order_or_404(user, order_public_id)
    data = create_schema.load(request.get_json(silent=True) or {})
    review = review_service.create_review(
        user, order, data["target_type"], data["target_id"], data["rating"], data.get("body")
    )
    return success({"review": review.to_public_dict()}, message="Review submitted.", status_code=201)


@reviews_bp.patch("/reviews/<review_public_id>")
@require_role(UserRole.CUSTOMER.value)
def update_review(review_public_id):
    user = current_user()
    review = review_service.get_review_or_404(review_public_id)
    data = update_schema.load(request.get_json(silent=True) or {})
    review = review_service.update_review(review, user, data.get("rating"), data.get("body"))
    return success({"review": review.to_public_dict()}, message="Review updated.")


@reviews_bp.delete("/reviews/<review_public_id>")
@require_role(UserRole.CUSTOMER.value)
def withdraw_review(review_public_id):
    user = current_user()
    review = review_service.get_review_or_404(review_public_id)
    review_service.withdraw_review(review, user)
    return success(message="Review removed.")


@reviews_bp.post("/reviews/<review_public_id>/report")
@require_role(UserRole.CUSTOMER.value, UserRole.VENDOR.value, UserRole.RIDER.value)
def report_review(review_public_id):
    user = current_user()
    review = review_service.get_review_or_404(review_public_id)
    data = report_schema.load(request.get_json(silent=True) or {})
    report = review_service.report_review(review, user, data["reason"])
    return success({"report": report.to_public_dict()}, message="Review reported.", status_code=201)


@reviews_bp.post("/reviews/<review_public_id>/response")
@require_role(UserRole.VENDOR.value, UserRole.RIDER.value)
def respond_to_review(review_public_id):
    user = current_user()
    review = review_service.get_review_or_404(review_public_id)
    data = response_schema.load(request.get_json(silent=True) or {})
    review_service.respond_to_review(review, user, data["body"])
    return success({"review": review.to_public_dict()}, message="Response posted.")


@reviews_bp.get("/vendors/<vendor_public_id>/reviews")
def list_vendor_public_reviews(vendor_public_id):
    """Public - a storefront's review list is part of catalog discovery,
    same visibility level as the vendor's own public catalog pages."""
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=20, type=int)
    pagination = review_service.list_reviews_for_target("VENDOR", vendor_public_id, page, per_page)
    return success(
        {
            "reviews": [r.to_public_dict() for r in pagination.items],
            "pagination": {"page": pagination.page, "per_page": pagination.per_page, "total": pagination.total, "pages": pagination.pages},
        }
    )
