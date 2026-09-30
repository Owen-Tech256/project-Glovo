"""My-own-reviews endpoints for vendors and riders (SRS 6: "allow vendors/
riders to view reviews of themselves"). Named vendor_routes.py to match
this codebase's per-module file-naming convention, but also serves the
rider-facing route since both are the same one-line query
(list_reviews_for_owner) against a different owner."""
from flask import Blueprint, request

from app.common.responses import success
from app.auth.decorators import require_role, current_user
from app.models.user import UserRole
from app.reviews import service as review_service

my_reviews_bp = Blueprint("my_reviews", __name__, url_prefix="/api/v1")


def _paginated_reviews():
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=20, type=int)
    pagination = review_service.list_reviews_for_owner(current_user(), page, per_page)
    return success(
        {
            "reviews": [r.to_public_dict() for r in pagination.items],
            "pagination": {"page": pagination.page, "per_page": pagination.per_page, "total": pagination.total, "pages": pagination.pages},
        }
    )


@my_reviews_bp.get("/vendor/reviews")
@require_role(UserRole.VENDOR.value)
def list_my_vendor_reviews():
    return _paginated_reviews()


@my_reviews_bp.get("/rider/reviews")
@require_role(UserRole.RIDER.value)
def list_my_rider_reviews():
    return _paginated_reviews()
