"""
Customer reviews of a vendor, rider, or (optionally) product, tied to a
specific delivered order (SRS 6: "Reviews must be linked to a completed
order to prevent fake reviews"). `target_type`/`target_id` is the same
polymorphic pattern already used by FinancialTransaction's
reference_type/reference_id - resolved by app/reviews/service.py, the one
place that knows how to look up a vendor/rider/product by id.
"""
import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class ReviewTargetType(str, enum.Enum):
    VENDOR = "VENDOR"
    RIDER = "RIDER"
    PRODUCT = "PRODUCT"


class ReviewStatus(str, enum.Enum):
    PUBLISHED = "PUBLISHED"
    PENDING_REVIEW = "PENDING_REVIEW"  # held for moderation after a report
    HIDDEN = "HIDDEN"                  # admin-moderated off public view, but not deleted
    REMOVED = "REMOVED"                # withdrawn by its author


# Statuses that count toward a target's public rating aggregate and that a
# public review listing shows.
VISIBLE_STATUSES = {ReviewStatus.PUBLISHED}


class Review(db.Model, PublicIdMixin, TimestampMixin):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    target_type = db.Column(db.Enum(ReviewTargetType, name="review_target_type", native_enum=False, length=20), nullable=False, index=True)
    target_id = db.Column(db.Integer, nullable=False, index=True)

    rating = db.Column(db.Integer, nullable=False)
    body = db.Column(db.Text, nullable=True)
    status = db.Column(
        db.Enum(ReviewStatus, name="review_status", native_enum=False, length=20),
        nullable=False, default=ReviewStatus.PUBLISHED, index=True,
    )
    edited_at = db.Column(db.DateTime(timezone=True), nullable=True)

    customer = db.relationship("User")
    order = db.relationship("Order", backref=db.backref("reviews", lazy="dynamic", cascade="all, delete-orphan"))
    reports = db.relationship("ReviewReport", backref="review", lazy="dynamic", cascade="all, delete-orphan")
    response = db.relationship("ReviewResponse", backref="review", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        db.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_reviews_rating_range"),
        db.UniqueConstraint("customer_id", "order_id", "target_type", "target_id", name="uq_reviews_identity"),
        db.Index("ix_reviews_target_status", "target_type", "target_id", "status"),
    )

    def to_public_dict(self, include_response: bool = True) -> dict:
        data = {
            "id": self.public_id,
            "customer_id": self.customer.public_id if self.customer else None,
            "customer_name": self.customer.full_name if self.customer else None,
            "order_id": self.order.public_id if self.order else None,
            "target_type": self.target_type.value if isinstance(self.target_type, ReviewTargetType) else self.target_type,
            "rating": self.rating,
            "body": self.body,
            "status": self.status.value if isinstance(self.status, ReviewStatus) else self.status,
            "edited_at": self.edited_at.isoformat() if self.edited_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_response and self.response is not None:
            data["response"] = self.response.to_public_dict()
        return data

    def __repr__(self):  # pragma: no cover
        return f"<Review {self.public_id} {self.target_type}:{self.target_id} rating={self.rating}>"


class ReviewReportStatus(str, enum.Enum):
    PENDING = "PENDING"
    REVIEWED = "REVIEWED"
    DISMISSED = "DISMISSED"


class ReviewReport(db.Model, PublicIdMixin, TimestampMixin):
    __tablename__ = "review_reports"

    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, db.ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    reporter_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reason = db.Column(db.String(500), nullable=False)
    status = db.Column(
        db.Enum(ReviewReportStatus, name="review_report_status", native_enum=False, length=20),
        nullable=False, default=ReviewReportStatus.PENDING, index=True,
    )
    resolved_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)

    reporter = db.relationship("User", foreign_keys=[reporter_user_id])

    __table_args__ = (
        db.UniqueConstraint("review_id", "reporter_user_id", name="uq_review_reports_identity"),
    )

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "review_id": self.review.public_id if self.review else None,
            "reporter_id": self.reporter.public_id if self.reporter else None,
            "reason": self.reason,
            "status": self.status.value if isinstance(self.status, ReviewReportStatus) else self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<ReviewReport review_id={self.review_id} {self.status}>"


class ReviewResponseStatus(str, enum.Enum):
    PUBLISHED = "PUBLISHED"
    HIDDEN = "HIDDEN"


class ReviewResponse(db.Model, PublicIdMixin, TimestampMixin):
    """A vendor's or rider's single reply to a review of them (SRS 6:
    "allow vendors/riders to respond to reviews"). Admin may also hide a
    response independently of the review it replies to."""

    __tablename__ = "review_responses"

    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, db.ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    responder_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(
        db.Enum(ReviewResponseStatus, name="review_response_status", native_enum=False, length=20),
        nullable=False, default=ReviewResponseStatus.PUBLISHED,
    )

    responder = db.relationship("User")

    def to_public_dict(self) -> dict:
        return {
            "body": self.body,
            "status": self.status.value if isinstance(self.status, ReviewResponseStatus) else self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<ReviewResponse review_id={self.review_id}>"
