from flask import Blueprint, request

from app.common.responses import success
from app.auth.decorators import require_role, current_user
from app.models.user import UserRole
from app.notifications import service as notification_service
from app.notifications.schemas import NotificationPreferenceUpdateSchema

notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/v1/notifications")

preference_schema = NotificationPreferenceUpdateSchema()

_ANY_ROLE = (UserRole.CUSTOMER.value, UserRole.VENDOR.value, UserRole.RIDER.value, UserRole.ADMIN.value)


@notifications_bp.get("")
@require_role(*_ANY_ROLE)
def list_notifications():
    user = current_user()
    unread_only = request.args.get("unread_only", "false").lower() == "true"
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=20, type=int)
    pagination = notification_service.list_notifications(user, unread_only, page, per_page)
    return success(
        {
            "notifications": [n.to_public_dict() for n in pagination.items],
            "unread_count": notification_service.unread_count(user),
            "pagination": {"page": pagination.page, "per_page": pagination.per_page, "total": pagination.total, "pages": pagination.pages},
        }
    )


@notifications_bp.patch("/<notification_public_id>/read")
@require_role(*_ANY_ROLE)
def mark_read(notification_public_id):
    user = current_user()
    notification = notification_service.mark_read(user, notification_public_id)
    return success({"notification": notification.to_public_dict()})


@notifications_bp.post("/read-all")
@require_role(*_ANY_ROLE)
def mark_all_read():
    user = current_user()
    updated = notification_service.mark_all_read(user)
    return success({"updated": updated}, message="All notifications marked as read.")


@notifications_bp.get("/preferences")
@require_role(*_ANY_ROLE)
def get_preferences():
    user = current_user()
    prefs = notification_service.get_preferences(user)
    return success({"preferences": [p.to_public_dict() for p in prefs]})


@notifications_bp.put("/preferences")
@require_role(*_ANY_ROLE)
def set_preference():
    user = current_user()
    data = preference_schema.load(request.get_json(silent=True) or {})
    pref = notification_service.set_preference(user, data["category"], data["channel"], data["enabled"])
    return success({"preference": pref.to_public_dict()}, message="Preference updated.")
