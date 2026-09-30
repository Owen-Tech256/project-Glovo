"""
Admin role/permission management (SRS 8). Seeds the six named roles from
the SRS's Admin Roles table plus their permissions lazily, the same
get-or-create convention used for NotificationTemplate rows (Phase 6,
app/notifications/templates.py:get_or_create_template) rather than a
migration-time data insert - no prior phase migration seeds rows either,
they all provision defaults from application code on first use. Here that
means `ensure_seeded()` runs once per process the first time anything
touches the roles/permissions themselves (`list_roles`, `list_permissions`,
`get_role_or_404`, `create_role` - see `_ensure_seeded_once` below), plus
once explicitly from the test suite's `app` fixture, since tests build
their schema via `db.create_all()` and exercise fixtures that query
AdminRole directly before any of those functions necessarily runs.
`ensure_seeded` itself is idempotent (checked by name/key), so calling it
more than once, from more than one place, is always harmless.

`is_super_admin`/`has_permission` never depend on seeding having happened:
the common case (`admin_role_id IS NULL`) is a plain column check with no
query against AdminRole/AdminPermission at all, so an admin's core access
never hinges on this bootstrap having run yet.

`is_super_admin`/`has_permission` are the only two functions the rest of
the codebase needs - `app.auth.decorators.require_admin_permission` calls
straight through to them, and nowhere else in this codebase should query
AdminRole/AdminPermission directly for an authorization decision.
"""
from app.extensions import db
from app.common.errors import NotFoundError, ValidationAppError, ConflictError
from app.models.user import User, UserRole
from app.models.admin_role import AdminRole, AdminPermission, AdminRoleStatus

# --- Seed data ---------------------------------------------------------

PERMISSIONS: list[tuple[str, str]] = [
    ("users.manage", "View and update any user account (suspend/activate/disable)."),
    ("vendors.manage", "Manage vendor and branch records and their status."),
    ("riders.manage", "Manage rider onboarding, documents, and status."),
    ("orders.view", "View any order and its status history."),
    ("deliveries.manage", "View and reassign deliveries."),
    ("finance.view", "View payments, refunds, payouts, and commission rules."),
    ("finance.manage", "Approve/reject/retry refunds and payouts; manage commission rules."),
    ("promotions.moderate", "View and moderate promotions and ad campaigns."),
    ("reviews.moderate", "View and moderate reviews and review reports."),
    ("support.view", "View support tickets and their public conversation."),
    ("support.manage", "Assign tickets, post internal notes, and change ticket status."),
    ("disputes.view", "View disputes, evidence, and their action history."),
    ("disputes.manage", "Investigate disputes and record non-financial actions."),
    ("disputes.financial_action", "Resolve a dispute with a refund via Phase 5 services."),
    ("analytics.view", "View analytics dashboards."),
    ("reports.manage", "Create report definitions and request exports."),
    ("audit.view", "View the platform audit trail."),
    ("roles.manage", "Manage admin roles, permissions, and staff assignments."),
]

SEED_ROLES: dict[str, tuple[str, list[str]]] = {
    "SUPER_ADMIN": ("Full platform administration.", [key for key, _ in PERMISSIONS]),
    "OPERATIONS_ADMIN": (
        "Orders, deliveries, vendors, riders, incidents.",
        ["users.manage", "vendors.manage", "riders.manage", "orders.view", "deliveries.manage",
         "support.view", "support.manage", "disputes.view", "disputes.manage", "analytics.view", "reports.manage"],
    ),
    "FINANCE_ADMIN": (
        "Payments, refunds, commissions, wallets, payouts.",
        ["finance.view", "finance.manage", "disputes.view", "disputes.financial_action", "analytics.view", "reports.manage"],
    ),
    "SUPPORT_AGENT": (
        "Tickets and permitted dispute workflows.",
        ["support.view", "support.manage", "disputes.view", "disputes.manage", "orders.view"],
    ),
    "MODERATOR": (
        "Reviews and content moderation.",
        ["promotions.moderate", "reviews.moderate"],
    ),
    "ANALYST": (
        "Read-only analytics/reports.",
        ["analytics.view", "reports.manage", "orders.view", "finance.view"],
    ),
}


def ensure_seeded() -> None:
    changed = False
    by_key = {p.key: p for p in AdminPermission.query.all()}
    for key, description in PERMISSIONS:
        if key not in by_key:
            perm = AdminPermission(key=key, description=description)
            db.session.add(perm)
            by_key[key] = perm
            changed = True

    if changed:
        db.session.flush()

    by_name = {r.name: r for r in AdminRole.query.all()}
    for name, (description, perm_keys) in SEED_ROLES.items():
        role = by_name.get(name)
        if role is None:
            role = AdminRole(name=name, description=description, is_system=True)
            db.session.add(role)
            by_name[name] = role
            changed = True
        role.permissions = [by_key[k] for k in perm_keys]

    if changed:
        db.session.commit()


_seeded_this_process = False


def _ensure_seeded_once() -> None:
    """Cheap per-process guard around `ensure_seeded()` so the RBAC
    management endpoints (the only callers - see module docstring) don't
    pay two extra queries on every single call once a process has already
    confirmed the seed exists."""
    global _seeded_this_process
    if not _seeded_this_process:
        ensure_seeded()
        _seeded_this_process = True


# --- Authorization -------------------------------------------------------

def is_super_admin(user: User) -> bool:
    if user.role != UserRole.ADMIN:
        return False
    # NULL admin_role = unrestricted (see User.admin_role_id docstring).
    if user.admin_role_id is None:
        return True
    return user.admin_role is not None and user.admin_role.name == "SUPER_ADMIN"


def has_permission(user: User, permission_key: str) -> bool:
    if is_super_admin(user):
        return True
    if user.role != UserRole.ADMIN or user.admin_role is None:
        return False
    if user.admin_role.status != AdminRoleStatus.ACTIVE:
        return False
    return permission_key in user.admin_role.permission_keys()


# --- Role/permission CRUD (SUPER_ADMIN only, enforced by the route layer) -

def list_permissions() -> list[AdminPermission]:
    _ensure_seeded_once()
    return AdminPermission.query.order_by(AdminPermission.key).all()


def list_roles() -> list[AdminRole]:
    _ensure_seeded_once()
    return AdminRole.query.order_by(AdminRole.name).all()


def get_role_or_404(role_public_id: str) -> AdminRole:
    _ensure_seeded_once()
    role = AdminRole.query.filter_by(public_id=role_public_id).first()
    if role is None:
        raise NotFoundError("Admin role not found.")
    return role


def create_role(name: str, description: str | None, permission_keys: list[str]) -> AdminRole:
    _ensure_seeded_once()
    if AdminRole.query.filter_by(name=name).first():
        raise ConflictError("A role with this name already exists.")
    perms = _resolve_permissions(permission_keys)
    role = AdminRole(name=name, description=description, is_system=False, permissions=perms)
    db.session.add(role)
    db.session.commit()
    return role


def update_role(role: AdminRole, description: str | None = None, permission_keys: list[str] | None = None,
                 status: str | None = None) -> AdminRole:
    if role.is_system and permission_keys is not None and role.name == "SUPER_ADMIN":
        raise ValidationAppError("SUPER_ADMIN's permissions cannot be narrowed.", code="ROLE_IMMUTABLE")
    if description is not None:
        role.description = description
    if permission_keys is not None:
        role.permissions = _resolve_permissions(permission_keys)
    if status is not None:
        if role.is_system and role.name == "SUPER_ADMIN":
            raise ValidationAppError("SUPER_ADMIN cannot be disabled.", code="ROLE_IMMUTABLE")
        role.status = AdminRoleStatus(status)
    db.session.commit()
    return role


def _resolve_permissions(permission_keys: list[str]) -> list[AdminPermission]:
    rows = AdminPermission.query.filter(AdminPermission.key.in_(permission_keys)).all()
    found = {r.key for r in rows}
    missing = set(permission_keys) - found
    if missing:
        raise ValidationAppError(f"Unknown permission key(s): {', '.join(sorted(missing))}.", code="UNKNOWN_PERMISSION")
    return rows


def assign_staff_role(staff_user: User, role_public_id: str | None) -> User:
    if staff_user.role != UserRole.ADMIN:
        raise ValidationAppError("Only an ADMIN account can be assigned an admin role.", code="NOT_AN_ADMIN")
    if role_public_id is None:
        staff_user.admin_role_id = None
    else:
        role = get_role_or_404(role_public_id)
        staff_user.admin_role_id = role.id
    db.session.commit()
    return staff_user


def list_staff(role_public_id: str | None = None, page: int = 1, per_page: int = 20):
    query = User.query.filter(User.role == UserRole.ADMIN)
    if role_public_id:
        role = get_role_or_404(role_public_id)
        query = query.filter(User.admin_role_id == role.id)
    return query.order_by(User.created_at.desc()).paginate(
        page=max(page, 1), per_page=max(min(per_page, 100), 1), error_out=False
    )
