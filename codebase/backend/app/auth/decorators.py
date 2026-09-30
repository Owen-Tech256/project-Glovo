"""
Reusable, stackable authorization decorators.

    @auth_bp.route("/some-admin-endpoint")
    @require_auth
    @require_role("ADMIN")
    def some_admin_endpoint():
        ...

    @users_bp.route("/users/<public_id>")
    @require_owner_or_role("public_id", "ADMIN")
    def get_user(public_id):
        ...

Every protected endpoint in this application is expected to go through one
of these, which guarantees, in order:
  1. The request carries a valid, non-expired access token.
  2. The referenced user still exists.
  3. The user's account status is ACTIVE (not SUSPENDED/DISABLED).
  4. (require_role)          the user's role is one of the allowed roles.
  4. (require_owner_or_role) the user IS the resource owner, OR their role
                              is one of the allowed override roles.

Frontend route guards are a UX convenience only - every one of these checks
is enforced here, server-side, regardless of what the client sends.
"""
from functools import wraps

from flask import g, request, current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

from app.common.errors import AuthenticationError, AccountNotActiveError, AuthorizationError
from app.models.user import User


def _authenticate() -> User:
    verify_jwt_in_request()
    public_id = get_jwt_identity()
    user = User.query.filter_by(public_id=public_id).first()
    if user is None:
        raise AuthenticationError("The account for this session no longer exists.")
    if not user.is_active:
        raise AccountNotActiveError(f"This account is {user.status.value.lower()}.")
    g.current_user = user
    return user


def require_auth(fn):
    """Verifies authentication + active status only. No role restriction."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        _authenticate()
        return fn(*args, **kwargs)

    return wrapper


def require_role(*allowed_roles: str):
    """Verifies authentication + active status + role membership."""
    allowed = {r.value if hasattr(r, "value") else r for r in allowed_roles}

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = _authenticate()
            if user.role.value not in allowed:
                if hasattr(current_app, "security_logger"):
                    current_app.security_logger.authorization_failure(
                        user.public_id, ",".join(sorted(allowed)), request.remote_addr, request.path
                    )
                raise AuthorizationError()
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def require_owner_or_role(url_param: str, *override_roles: str):
    """Verifies authentication + active status, then allows the request only
    if the authenticated user owns the resource identified by `url_param`
    (matched against the user's public_id) OR holds one of the override
    roles (e.g. ADMIN). This is what prevents a user from reaching another
    user's private data simply by changing an ID in the URL."""
    overrides = {r.value if hasattr(r, "value") else r for r in override_roles}

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = _authenticate()
            target_public_id = kwargs.get(url_param)
            is_owner = target_public_id is not None and target_public_id == user.public_id
            is_override = user.role.value in overrides
            if not (is_owner or is_override):
                if hasattr(current_app, "security_logger"):
                    current_app.security_logger.authorization_failure(
                        user.public_id, f"owner-or:{','.join(sorted(overrides))}", request.remote_addr, request.path
                    )
                raise AuthorizationError()
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def require_admin_permission(*permission_keys: str):
    """Verifies authentication + active status + role == ADMIN + the admin
    holds at least one of the given fine-grained permissions (Phase 7 SRS
    8: "Permissions are enforced server-side; UI visibility is not a
    security boundary"). A SUPER_ADMIN, and any admin with no admin_role
    assigned at all (NULL = unrestricted, see User.admin_role_id), always
    passes - see app/rbac/service.py:has_permission for the precise rule.
    This is additive to, not a replacement for, `require_role("ADMIN")`:
    every Phase 7 admin route uses this instead; Phase 1-6 admin routes
    are unchanged."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = _authenticate()
            if user.role.value != "ADMIN":
                raise AuthorizationError()
            from app.rbac.service import has_permission

            if not any(has_permission(user, key) for key in permission_keys):
                if hasattr(current_app, "security_logger"):
                    current_app.security_logger.authorization_failure(
                        user.public_id, ",".join(permission_keys), request.remote_addr, request.path
                    )
                raise AuthorizationError()
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def current_user() -> User:
    return g.current_user
