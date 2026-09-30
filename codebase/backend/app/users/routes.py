from flask import Blueprint, request

from app.extensions import db
from app.common.responses import success
from app.common.errors import NotFoundError
from app.models.user import User, UserRole
from app.auth.decorators import require_auth, require_role, require_owner_or_role, current_user
from app.auth.schemas import UpdateMeSchema

users_bp = Blueprint("users", __name__, url_prefix="/api/v1/users")

update_me_schema = UpdateMeSchema()


@users_bp.patch("/me")
@require_auth
def update_me():
    data = update_me_schema.load(request.get_json(silent=True) or {})
    user = current_user()
    if "full_name" in data:
        user.full_name = data["full_name"].strip()
    db.session.commit()
    return success({"user": user.to_public_dict()}, message="Profile updated.")


@users_bp.get("/<public_id>")
@require_owner_or_role("public_id", UserRole.ADMIN.value)
def get_user(public_id):
    """A user may fetch their own record; an ADMIN may fetch any record.
    This is the endpoint the ownership test suite exercises: changing the
    `public_id` in the URL to someone else's must never succeed for a
    non-admin caller."""
    user = User.query.filter_by(public_id=public_id).first()
    if user is None:
        raise NotFoundError("User not found.")
    return success({"user": user.to_public_dict()})


@users_bp.get("")
@require_role(UserRole.ADMIN.value)
def list_users():
    """Admin-only, paginated foundation for future user-management screens.
    Deliberately minimal in Phase 1: filtering/sorting beyond role/status is
    left for a later phase."""
    page = request.args.get("page", default=1, type=int)
    per_page = min(request.args.get("per_page", default=20, type=int), 100)
    role_filter = request.args.get("role")

    query = User.query
    if role_filter:
        query = query.filter(User.role == role_filter)

    pagination = query.order_by(User.created_at.desc()).paginate(
        page=max(page, 1), per_page=max(per_page, 1), error_out=False
    )
    return success(
        {
            "users": [u.to_public_dict() for u in pagination.items],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "total_pages": pagination.pages,
            },
        }
    )
