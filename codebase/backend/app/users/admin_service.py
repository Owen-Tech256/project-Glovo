"""Admin oversight of user accounts (Phase 7 SRS 7: "User/vendor/rider
management"). Vendor/branch/rider-onboarding management already exists
from Phases 2/4 (app/api/admin_catalog_routes.py, admin_logistics_routes.py)
- this fills the one gap Phase 1-6 left: a plain account-level view/action
that works for any role, including CUSTOMER accounts which have no other
admin surface at all."""
from app.extensions import db
from app.common.errors import NotFoundError, ValidationAppError
from app.models.user import User, UserRole, UserStatus


def list_users(role: str | None = None, status: str | None = None, query: str | None = None,
                page: int = 1, per_page: int = 20):
    q = User.query
    if role:
        q = q.filter(User.role == role)
    if status:
        q = q.filter(User.status == status)
    if query:
        like = f"%{query}%"
        q = q.filter(db.or_(User.full_name.ilike(like), User.email.ilike(like)))
    return q.order_by(User.created_at.desc()).paginate(
        page=max(page, 1), per_page=max(min(per_page, 100), 1), error_out=False
    )


def get_user_or_404(public_id: str) -> User:
    user = User.query.filter_by(public_id=public_id).first()
    if user is None:
        raise NotFoundError("User not found.")
    return user


def get_user_detail(public_id: str) -> dict:
    user = get_user_or_404(public_id)
    data = user.to_public_dict()
    if user.role == UserRole.VENDOR:
        from app.models.vendor import Vendor

        vendor = Vendor.query.filter_by(user_id=user.id).first()
        if vendor:
            data["vendor"] = {"id": vendor.public_id, "name": vendor.name, "status": vendor.status.value}
    elif user.role == UserRole.RIDER:
        from app.models.rider import Rider

        rider = Rider.query.filter_by(user_id=user.id).first()
        if rider:
            data["rider"] = {
                "id": rider.public_id,
                "onboarding_status": rider.onboarding_status.value,
                "operational_status": rider.operational_status.value,
            }
    return data


def update_status(actor, target_public_id: str, status: str, reason: str | None, ip_address: str | None) -> User:
    user = get_user_or_404(target_public_id)
    if user.id == actor.id:
        raise ValidationAppError("You cannot change your own account status.", code="CANNOT_SELF_MODIFY")
    before_status = user.status.value
    user.status = UserStatus(status)
    db.session.commit()

    from app.audit.service import record

    record(actor, "USER_STATUS_CHANGED", entity_type="USER", entity_id=user.public_id,
           before={"status": before_status}, after={"status": user.status.value, "reason": reason},
           ip_address=ip_address)
    return user
