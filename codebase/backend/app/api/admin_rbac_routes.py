"""Admin role/permission management (SRS 7/8): SUPER_ADMIN-only surface
for defining what each operational-staff role can do and assigning roles
to staff accounts."""
from flask import Blueprint, request

from app.auth.decorators import require_admin_permission, current_user
from app.common.responses import success
from app.common.errors import NotFoundError
from app.rbac import service as rbac_service
from app.rbac.schemas import RoleCreateSchema, RoleUpdateSchema, AssignStaffRoleSchema
from app.models.user import User

admin_rbac_bp = Blueprint("admin_rbac", __name__, url_prefix="/api/v1/admin")


def _pagination(pagination):
    return {
        "page": pagination.page, "per_page": pagination.per_page,
        "total": pagination.total, "total_pages": pagination.pages,
    }


@admin_rbac_bp.route("/permissions", methods=["GET"])
@require_admin_permission("roles.manage")
def list_permissions():
    return success({"permissions": [p.to_public_dict() for p in rbac_service.list_permissions()]})


@admin_rbac_bp.route("/roles", methods=["GET"])
@require_admin_permission("roles.manage")
def list_roles():
    return success({"roles": [r.to_public_dict() for r in rbac_service.list_roles()]})


@admin_rbac_bp.route("/roles", methods=["POST"])
@require_admin_permission("roles.manage")
def create_role():
    data = RoleCreateSchema().load(request.get_json(silent=True) or {})
    role = rbac_service.create_role(data["name"], data.get("description"), data.get("permission_keys") or [])
    return success({"role": role.to_public_dict()}, message="Role created.", status_code=201)


@admin_rbac_bp.route("/roles/<role_public_id>", methods=["PATCH"])
@require_admin_permission("roles.manage")
def update_role(role_public_id):
    data = RoleUpdateSchema().load(request.get_json(silent=True) or {})
    role = rbac_service.get_role_or_404(role_public_id)
    role = rbac_service.update_role(
        role, description=data.get("description"), permission_keys=data.get("permission_keys"),
        status=data.get("status"),
    )
    return success({"role": role.to_public_dict()}, message="Role updated.")


@admin_rbac_bp.route("/staff", methods=["GET"])
@require_admin_permission("roles.manage")
def list_staff():
    pagination = rbac_service.list_staff(
        role_public_id=request.args.get("role_id"),
        page=request.args.get("page", default=1, type=int),
        per_page=request.args.get("per_page", default=20, type=int),
    )
    return success({"staff": [u.to_public_dict() for u in pagination.items], "pagination": _pagination(pagination)})


@admin_rbac_bp.route("/staff/<user_public_id>/role", methods=["PATCH"])
@require_admin_permission("roles.manage")
def assign_staff_role(user_public_id):
    data = AssignStaffRoleSchema().load(request.get_json(silent=True) or {})
    staff_user = User.query.filter_by(public_id=user_public_id).first()
    if staff_user is None:
        raise NotFoundError("User not found.")
    staff_user = rbac_service.assign_staff_role(staff_user, data.get("role_id"))

    from app.audit.service import record

    record(current_user(), "ADMIN_ROLE_ASSIGNED", entity_type="USER", entity_id=staff_user.public_id,
           after={"admin_role": staff_user.admin_role.name if staff_user.admin_role else None})
    return success({"staff": staff_user.to_public_dict()}, message="Staff role updated.")
