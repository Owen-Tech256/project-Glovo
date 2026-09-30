import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class UserRole(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    VENDOR = "VENDOR"
    RIDER = "RIDER"
    ADMIN = "ADMIN"


class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DISABLED = "DISABLED"


class User(db.Model, PublicIdMixin, TimestampMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(32), unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(
        db.Enum(UserRole, name="user_role", native_enum=False, length=20),
        nullable=False,
        index=True,
    )
    status = db.Column(
        db.Enum(UserStatus, name="user_status", native_enum=False, length=20),
        nullable=False,
        default=UserStatus.ACTIVE,
        index=True,
    )

    is_email_verified = db.Column(db.Boolean, nullable=False, default=False)
    is_phone_verified = db.Column(db.Boolean, nullable=False, default=False)
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Phase 7: fine-grained operational-staff role, meaningful only when
    # role == ADMIN. NULL is deliberate and backward-compatible - it means
    # "unrestricted", the behavior every ADMIN account already had in
    # Phases 1-6 - see app/rbac/service.py:is_super_admin.
    admin_role_id = db.Column(db.Integer, db.ForeignKey("admin_roles.id", ondelete="SET NULL"), nullable=True, index=True)

    refresh_tokens = db.relationship(
        "RefreshToken", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )
    password_reset_tokens = db.relationship(
        "PasswordResetToken", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )
    audit_events = db.relationship("AuditEvent", backref="user", lazy="dynamic")

    __table_args__ = (
        db.Index("ix_users_role_status", "role", "status"),
    )

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE

    def to_public_dict(self) -> dict:
        """Safe representation returned by the API. Never includes
        password_hash or any token material."""
        data = {
            "id": self.public_id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "role": self.role.value if isinstance(self.role, UserRole) else self.role,
            "status": self.status.value if isinstance(self.status, UserStatus) else self.status,
            "is_email_verified": self.is_email_verified,
            "is_phone_verified": self.is_phone_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }
        if self.role == UserRole.ADMIN:
            data["admin_role"] = self.admin_role.name if self.admin_role else None
        return data

    def __repr__(self):  # pragma: no cover
        return f"<User {self.public_id} {self.email} {self.role}>"
