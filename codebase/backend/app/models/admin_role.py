"""
Fine-grained permissions for operational staff (Phase 7 SRS 8: "Role/
permission management for operational staff"). This sits *on top of* the
existing flat `UserRole.ADMIN` from Phase 1 - it does not replace it.
Every route still requires `role == ADMIN` first (via `require_role`/
`require_admin_permission`); an `AdminRole` only narrows what a given
ADMIN account may do once inside the admin surface.

Backward compatibility is deliberate: `User.admin_role_id` is nullable, and
a NULL value means "unrestricted" (every existing Phase 1-6 admin account,
and any admin created without an explicit role assignment, keeps exactly
the full access it already had - see `app/rbac/service.py:is_super_admin`).
Assigning one of the seeded roles below is how a SUPER_ADMIN scopes a new
staff account down to just what its job needs.
"""
import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class AdminRoleStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


admin_role_permissions = db.Table(
    "admin_role_permissions",
    db.Column("role_id", db.Integer, db.ForeignKey("admin_roles.id", ondelete="CASCADE"), primary_key=True),
    db.Column("permission_id", db.Integer, db.ForeignKey("admin_permissions.id", ondelete="CASCADE"), primary_key=True),
)


class AdminRole(db.Model, PublicIdMixin, TimestampMixin):
    """SRS 8's SUPER_ADMIN/OPERATIONS_ADMIN/FINANCE_ADMIN/SUPPORT_AGENT/
    MODERATOR/ANALYST are seeded rows (see app/rbac/service.py:SEED_ROLES),
    not hardcoded values - a SUPER_ADMIN can add or adjust roles as the
    operations team's structure evolves, which is why this is a table and
    not another enum."""

    __tablename__ = "admin_roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True)
    is_system = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(
        db.Enum(AdminRoleStatus, name="admin_role_status", native_enum=False, length=20),
        nullable=False, default=AdminRoleStatus.ACTIVE,
    )

    permissions = db.relationship("AdminPermission", secondary=admin_role_permissions, lazy="joined")
    staff = db.relationship("User", backref="admin_role", lazy="dynamic")

    def permission_keys(self) -> set[str]:
        return {p.key for p in self.permissions}

    def to_public_dict(self, include_permissions: bool = True) -> dict:
        data = {
            "id": self.public_id,
            "name": self.name,
            "description": self.description,
            "is_system": self.is_system,
            "status": self.status.value if isinstance(self.status, AdminRoleStatus) else self.status,
            "staff_count": self.staff.count(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_permissions:
            data["permissions"] = sorted(self.permission_keys())
        return data

    def __repr__(self):  # pragma: no cover
        return f"<AdminRole {self.name}>"


class AdminPermission(db.Model):
    """A single grantable capability, e.g. `support.manage`,
    `finance.view`. Keys are dotted `area.verb` strings so the admin RBAC
    UI can group them by area without a separate category column."""

    __tablename__ = "admin_permissions"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=False)

    def to_public_dict(self) -> dict:
        return {"key": self.key, "description": self.description}

    def __repr__(self):  # pragma: no cover
        return f"<AdminPermission {self.key}>"
