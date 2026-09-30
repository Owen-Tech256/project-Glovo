"""
Review eligibility, CRUD, moderation, and rating aggregation (SRS 6).

`target_type`/`target_id` is resolved to a public_id-facing dict at read
time by `_resolve_target_info` - the one place that knows how to look up a
vendor/rider/product's name and owning user (for response-authorship
checks) by internal id, mirroring the polymorphic-resolution helpers in
app/promotions/service.py and app/advertising/service.py.

Rating aggregates on Vendor/Rider/Product are *always* a full recompute
over that target's current PUBLISHED reviews (`_recompute_rating`), never
an incremental +/-1 - so a moderation action, an edit, or a withdrawal can
never leave the cached average/count out of sync with the underlying
reviews (SRS 6: "safely recalculated when reviews are added/edited/
removed").
"""
from decimal import Decimal, ROUND_HALF_UP

from app.extensions import db
from app.common.errors import NotFoundError, ValidationAppError, AuthorizationError
from app.models.review import (
    Review, ReviewTargetType, ReviewStatus, VISIBLE_STATUSES,
    ReviewReport, ReviewReportStatus, ReviewResponse, ReviewResponseStatus,
)
from app.models.order import Order, OrderStatus

THREE_PLACES = Decimal("0.01")


def _resolve_target_info(target_type: ReviewTargetType, target_id: int) -> dict | None:
    """Returns {"name": ..., "public_id": ..., "owner_user_id": ...} or
    None if the target no longer exists. owner_user_id is who may author a
    ReviewResponse (a vendor's account owner, or a rider's own user
    account)."""
    if target_type == ReviewTargetType.VENDOR:
        from app.models.vendor import Vendor

        row = db.session.get(Vendor, target_id)
        return {"name": row.name, "public_id": row.public_id, "owner_user_id": row.user_id} if row else None
    if target_type == ReviewTargetType.RIDER:
        from app.models.rider import Rider

        row = db.session.get(Rider, target_id)
        return {"name": row.user.full_name, "public_id": row.public_id, "owner_user_id": row.user_id} if row else None
    from app.models.product import Product

    row = db.session.get(Product, target_id)
    return {"name": row.name, "public_id": row.public_id, "owner_user_id": None} if row else None


def _recompute_rating(target_type: ReviewTargetType, target_id: int) -> None:
    result = (
        db.session.query(db.func.avg(Review.rating), db.func.count(Review.id))
        .filter(Review.target_type == target_type, Review.target_id == target_id, Review.status == ReviewStatus.PUBLISHED)
        .one()
    )
    average, count = result
    average = Decimal(str(average)).quantize(THREE_PLACES, rounding=ROUND_HALF_UP) if average is not None else None
    count = count or 0

    if target_type == ReviewTargetType.VENDOR:
        from app.models.vendor import Vendor

        row = db.session.get(Vendor, target_id)
    elif target_type == ReviewTargetType.RIDER:
        from app.models.rider import Rider

        row = db.session.get(Rider, target_id)
    else:
        from app.models.product import Product

        row = db.session.get(Product, target_id)
    if row is not None:
        row.rating_average = average
        row.rating_count = count


# --- Eligibility -----------------------------------------------------------

def _reviewable_target_ids(order: Order, customer) -> list[tuple[ReviewTargetType, int]]:
    """The internal-id form of the reviewable target list - what
    eligibility checks compare against. get_reviewable_targets (below)
    maps this to the public-facing shape."""
    if order.customer_id != customer.id:
        raise AuthorizationError("This order does not belong to you.")
    if order.status != OrderStatus.DELIVERED:
        return []

    from flask import current_app

    targets: list[tuple[ReviewTargetType, int]] = [(ReviewTargetType.VENDOR, order.branch.vendor_id)]
    if order.delivery and order.delivery.rider_id:
        targets.append((ReviewTargetType.RIDER, order.delivery.rider_id))
    if current_app.config.get("PRODUCT_REVIEWS_ENABLED", True):
        seen_products = set()
        for item in order.items:
            if item.product_id and item.product_id not in seen_products:
                seen_products.add(item.product_id)
                targets.append((ReviewTargetType.PRODUCT, item.product_id))
    return targets


def get_reviewable_targets(order: Order, customer) -> list[dict]:
    """Every (target_type, target_id) this order makes reviewable, each
    annotated with the customer's existing review of it (if any). An order
    must be DELIVERED (SRS 6: "linked to a completed order") - anything
    earlier in the lifecycle has nothing reviewable yet."""
    targets = _reviewable_target_ids(order, customer)

    existing = {
        (r.target_type, r.target_id): r
        for r in Review.query.filter_by(customer_id=customer.id, order_id=order.id).all()
    }
    results = []
    for target_type, target_id in targets:
        info = _resolve_target_info(target_type, target_id)
        if info is None:
            continue
        review = existing.get((target_type, target_id))
        results.append(
            {
                "target_type": target_type.value,
                "target_id": info["public_id"],
                "target_name": info["name"],
                "existing_review": review.to_public_dict() if review else None,
            }
        )
    return results


def _assert_reviewable(order: Order, customer, target_type: ReviewTargetType, target_id: int) -> None:
    """target_id here is the internal id (already resolved from the
    client's public_id by the caller) - compared against
    _reviewable_target_ids's internal-id list, not get_reviewable_targets's
    public-facing one."""
    valid_ids = set(_reviewable_target_ids(order, customer))
    if (target_type, target_id) not in valid_ids:
        raise ValidationAppError(
            "This order does not make that target reviewable.", code="REVIEW_TARGET_NOT_ELIGIBLE"
        )


# --- CRUD ------------------------------------------------------------------

def create_review(customer, order: Order, target_type_str: str, target_public_id: str, rating: int, body: str | None) -> Review:
    target_type = ReviewTargetType(target_type_str)
    target_id = _resolve_target_public_id(target_type, target_public_id)
    _assert_reviewable(order, customer, target_type, target_id)

    if Review.query.filter_by(customer_id=customer.id, order_id=order.id, target_type=target_type, target_id=target_id).first():
        raise ValidationAppError("You have already reviewed this on this order.", code="REVIEW_ALREADY_EXISTS")

    review = Review(
        customer_id=customer.id, order_id=order.id, target_type=target_type, target_id=target_id,
        rating=rating, body=body, status=ReviewStatus.PUBLISHED,
    )
    db.session.add(review)
    _recompute_rating(target_type, target_id)
    db.session.commit()
    return review


def _resolve_target_public_id(target_type: ReviewTargetType, target_public_id: str) -> int:
    if target_type == ReviewTargetType.VENDOR:
        from app.models.vendor import Vendor

        row = Vendor.query.filter_by(public_id=target_public_id).first()
    elif target_type == ReviewTargetType.RIDER:
        from app.models.rider import Rider

        row = Rider.query.filter_by(public_id=target_public_id).first()
    else:
        from app.models.product import Product

        row = Product.query.filter_by(public_id=target_public_id).first()
    if row is None:
        raise NotFoundError("Review target not found.")
    return row.id


def update_review(review: Review, customer, rating: int | None, body: str | None) -> Review:
    if review.customer_id != customer.id:
        raise AuthorizationError("You can only edit your own review.")
    if review.status == ReviewStatus.REMOVED:
        raise ValidationAppError("A removed review cannot be edited.", code="REVIEW_REMOVED")
    if rating is not None:
        review.rating = rating
    if body is not None:
        review.body = body
    from app.models.base import _utcnow

    review.edited_at = _utcnow()
    _recompute_rating(review.target_type, review.target_id)
    db.session.commit()
    return review


def withdraw_review(review: Review, customer) -> Review:
    if review.customer_id != customer.id:
        raise AuthorizationError("You can only remove your own review.")
    review.status = ReviewStatus.REMOVED
    _recompute_rating(review.target_type, review.target_id)
    db.session.commit()
    return review


def report_review(review: Review, reporter, reason: str) -> ReviewReport:
    if ReviewReport.query.filter_by(review_id=review.id, reporter_user_id=reporter.id).first():
        raise ValidationAppError("You have already reported this review.", code="REVIEW_ALREADY_REPORTED")
    report = ReviewReport(review_id=review.id, reporter_user_id=reporter.id, reason=reason)
    db.session.add(report)
    # Hold the review out of public view while a report is pending -
    # rating aggregates exclude it immediately rather than waiting for an
    # admin to get to the queue.
    if review.status == ReviewStatus.PUBLISHED:
        review.status = ReviewStatus.PENDING_REVIEW
        _recompute_rating(review.target_type, review.target_id)
    db.session.commit()
    return report


def respond_to_review(review: Review, responder, body: str) -> ReviewResponse:
    info = _resolve_target_info(review.target_type, review.target_id)
    if info is None or info.get("owner_user_id") != responder.id:
        raise AuthorizationError("You can only respond to reviews of yourself/your business.")
    if review.response is not None:
        review.response.body = body
        review.response.status = ReviewResponseStatus.PUBLISHED
    else:
        db.session.add(ReviewResponse(review_id=review.id, responder_user_id=responder.id, body=body))
    db.session.commit()
    return review.response


# --- Admin moderation ------------------------------------------------------

def moderate_review(review: Review, status: str) -> Review:
    review.status = ReviewStatus(status)
    _recompute_rating(review.target_type, review.target_id)
    db.session.commit()
    return review


def resolve_report(report: ReviewReport, admin_user, status: str) -> ReviewReport:
    report.status = ReviewReportStatus(status)
    report.resolved_by_user_id = admin_user.id
    from app.models.base import _utcnow

    report.resolved_at = _utcnow()
    db.session.commit()
    return report


# --- Lookups -------------------------------------------------------------

def get_review_or_404(review_public_id: str) -> Review:
    review = Review.query.filter_by(public_id=review_public_id).first()
    if review is None:
        raise NotFoundError("Review not found.")
    return review


def list_reviews_for_target(target_type: str, target_public_id: str, page: int = 1, per_page: int = 20):
    target_type_enum = ReviewTargetType(target_type)
    target_id = _resolve_target_public_id(target_type_enum, target_public_id)
    return (
        Review.query.filter(
            Review.target_type == target_type_enum, Review.target_id == target_id, Review.status.in_(VISIBLE_STATUSES)
        )
        .order_by(Review.created_at.desc())
        .paginate(page=max(page, 1), per_page=max(min(per_page, 100), 1), error_out=False)
    )


def list_reviews_for_owner(owner_user, page: int = 1, per_page: int = 20):
    """Reviews of the vendor/rider this user owns - for their own review-
    management page (SRS 6: "allow vendors/riders to view... reviews of
    themselves")."""
    from app.models.vendor import Vendor
    from app.models.rider import Rider

    vendor = Vendor.query.filter_by(user_id=owner_user.id).first()
    rider = Rider.query.filter_by(user_id=owner_user.id).first()
    filters = []
    if vendor:
        filters.append(db.and_(Review.target_type == ReviewTargetType.VENDOR, Review.target_id == vendor.id))
    if rider:
        filters.append(db.and_(Review.target_type == ReviewTargetType.RIDER, Review.target_id == rider.id))
    if not filters:
        return Review.query.filter(db.false()).paginate(page=1, per_page=per_page, error_out=False)
    return (
        Review.query.filter(db.or_(*filters))
        .order_by(Review.created_at.desc())
        .paginate(page=max(page, 1), per_page=max(min(per_page, 100), 1), error_out=False)
    )


def list_all_reviews(status: str | None = None, page: int = 1, per_page: int = 20):
    query = Review.query
    if status:
        query = query.filter(Review.status == status)
    return query.order_by(Review.created_at.desc()).paginate(
        page=max(page, 1), per_page=max(min(per_page, 100), 1), error_out=False
    )


def list_all_reports(status: str | None = None, page: int = 1, per_page: int = 20):
    query = ReviewReport.query
    if status:
        query = query.filter(ReviewReport.status == status)
    return query.order_by(ReviewReport.created_at.desc()).paginate(
        page=max(page, 1), per_page=max(min(per_page, 100), 1), error_out=False
    )


def get_report_or_404(report_public_id: str) -> ReviewReport:
    report = ReviewReport.query.filter_by(public_id=report_public_id).first()
    if report is None:
        raise NotFoundError("Review report not found.")
    return report
