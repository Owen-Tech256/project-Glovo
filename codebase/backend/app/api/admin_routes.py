from flask import Blueprint, request
from marshmallow import Schema, fields, validate

from app.common.responses import success
from app.models.user import User, UserRole, UserStatus
from app.auth.decorators import require_role, require_admin_permission, current_user
from app.users import admin_service

admin_bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")


class _UserStatusUpdateSchema(Schema):
    class Meta:
        unknown = "exclude"

    status = fields.String(required=True, validate=validate.OneOf([s.value for s in UserStatus]))
    reason = fields.String(required=False, allow_none=True, validate=validate.Length(max=500))


@admin_bp.get("/stats")
@require_role(UserRole.ADMIN.value)
def platform_stats():
    """Minimal platform-overview data for the Admin Dashboard placeholder.
    Intentionally limited to user counts - order/payment/analytics stats
    belong to later phases."""
    counts_by_role = {
        role.value: User.query.filter_by(role=role).count() for role in UserRole
    }
    counts_by_status = {
        status.value: User.query.filter_by(status=status).count() for status in UserStatus
    }
    return success(
        {
            "total_users": sum(counts_by_role.values()),
            "users_by_role": counts_by_role,
            "users_by_status": counts_by_status,
        }
    )


def _pagination(pagination):
    return {
        "page": pagination.page, "per_page": pagination.per_page,
        "total": pagination.total, "total_pages": pagination.pages,
    }


@admin_bp.get("/users")
@require_admin_permission("users.manage")
def list_users():
    pagination = admin_service.list_users(
        role=request.args.get("role"), status=request.args.get("status"), query=request.args.get("q"),
        page=request.args.get("page", default=1, type=int), per_page=request.args.get("per_page", default=20, type=int),
    )
    return success({"users": [u.to_public_dict() for u in pagination.items], "pagination": _pagination(pagination)})


@admin_bp.get("/users/<public_id>")
@require_admin_permission("users.manage")
def get_user(public_id):
    return success({"user": admin_service.get_user_detail(public_id)})


@admin_bp.patch("/users/<public_id>/status")
@require_admin_permission("users.manage")
def update_user_status(public_id):
    data = _UserStatusUpdateSchema().load(request.get_json(silent=True) or {})
    user = admin_service.update_status(current_user(), public_id, data["status"], data.get("reason"), request.remote_addr)
    return success({"user": user.to_public_dict()}, message="User status updated.")
