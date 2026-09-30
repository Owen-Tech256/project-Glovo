from flask import Blueprint, request, current_app

from app.extensions import limiter
from app.common.responses import success
from app.auth.schemas import (
    RegisterSchema,
    LoginSchema,
    RefreshSchema,
    LogoutSchema,
    ForgotPasswordSchema,
    ResetPasswordSchema,
)
from app.auth.decorators import require_auth, current_user
from app.auth import service

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

register_schema = RegisterSchema()
login_schema = LoginSchema()
refresh_schema = RefreshSchema()
logout_schema = LogoutSchema()
forgot_password_schema = ForgotPasswordSchema()
reset_password_schema = ResetPasswordSchema()


@auth_bp.post("/register")
@limiter.limit("10 per hour")
def register():
    data = register_schema.load(request.get_json(silent=True) or {})
    user = service.register_user(data, request.remote_addr, request.headers.get("User-Agent", ""))
    tokens = service.issue_token_pair(user)
    return success(
        {"user": user.to_public_dict(), **tokens},
        message="Registration successful.",
        status_code=201,
    )


@auth_bp.post("/login")
@limiter.limit("10 per minute")
def login():
    data = login_schema.load(request.get_json(silent=True) or {})
    user = service.authenticate_user(
        data["identifier"], data["password"], request.remote_addr, request.headers.get("User-Agent", "")
    )
    tokens = service.issue_token_pair(user)
    return success({"user": user.to_public_dict(), **tokens}, message="Login successful.")


@auth_bp.post("/logout")
@require_auth
def logout():
    data = logout_schema.load(request.get_json(silent=True) or {})
    service.logout_user(data["refresh_token"], current_user().public_id, request.remote_addr)
    return success(message="Logout successful.")


@auth_bp.post("/refresh")
@limiter.limit("30 per minute")
def refresh():
    data = refresh_schema.load(request.get_json(silent=True) or {})
    tokens = service.refresh_token_pair(data["refresh_token"], request.remote_addr)
    return success(tokens, message="Token refreshed.")


@auth_bp.get("/me")
@require_auth
def me():
    return success({"user": current_user().to_public_dict()})


@auth_bp.post("/forgot-password")
@limiter.limit("5 per hour")
def forgot_password():
    data = forgot_password_schema.load(request.get_json(silent=True) or {})
    raw_token = service.request_password_reset(data["email"], request.remote_addr)

    payload = {}
    # NEVER do this in a real production deployment - the token must only
    # ever be delivered out-of-band via a verified email address. It is
    # surfaced here only because Phase 1 has no email/SMS provider wired up
    # yet, and only when DEBUG is enabled, so local development and the
    # automated test suite can exercise the full reset flow end-to-end.
    if current_app.config.get("DEBUG") or current_app.config.get("TESTING"):
        payload["debug_reset_token"] = raw_token

    return success(
        payload,
        message="If an account with that email exists, a password reset link has been sent.",
    )


@auth_bp.post("/reset-password")
@limiter.limit("10 per hour")
def reset_password():
    data = reset_password_schema.load(request.get_json(silent=True) or {})
    service.complete_password_reset(data["token"], data["password"], request.remote_addr)
    return success(message="Password has been reset successfully. Please log in again.")
