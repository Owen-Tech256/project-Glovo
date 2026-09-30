"""
Token strategy
--------------
Access token:  a short-lived, stateless JWT (flask-jwt-extended). Carries the
               user's public_id as identity and role as a claim. Verified on
               every request without a DB lookup for the signature itself.

Refresh token: a long-lived, opaque random string. The RAW value is returned
               to the client exactly once (at login/refresh time) and never
               stored. Only its SHA-256 hash is persisted in `refresh_tokens`,
               which is what makes server-side revocation and rotation
               possible (a stateless JWT refresh token could not be revoked
               before its natural expiry).

Password reset token: same opaque-token-plus-hash approach as refresh
               tokens, stored in `password_reset_tokens`, single-use.
"""
import hashlib
import secrets
from datetime import datetime, timezone

from flask import current_app
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models.refresh_token import RefreshToken
from app.models.password_reset_token import PasswordResetToken


def utcnow():
    return datetime.now(timezone.utc)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def issue_access_token(user) -> str:
    return create_access_token(
        identity=user.public_id,
        additional_claims={"role": user.role.value, "status": user.status.value},
    )


def issue_refresh_token(user) -> str:
    raw_token = secrets.token_urlsafe(64)
    expires_delta = current_app.config["JWT_REFRESH_TOKEN_EXPIRES"]
    record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=utcnow() + expires_delta,
    )
    db.session.add(record)
    return raw_token


def get_valid_refresh_token_record(raw_token: str):
    token_hash = hash_token(raw_token)
    record = RefreshToken.query.filter_by(token_hash=token_hash).first()
    if record is None or not record.is_valid(utcnow()):
        return None
    return record


def revoke_refresh_token(record: RefreshToken):
    record.revoked_at = utcnow()


def revoke_all_refresh_tokens_for_user(user):
    now = utcnow()
    RefreshToken.query.filter_by(user_id=user.id, revoked_at=None).update({"revoked_at": now})


def issue_password_reset_token(user) -> str:
    raw_token = secrets.token_urlsafe(48)
    expires_delta = current_app.config["PASSWORD_RESET_TOKEN_EXPIRES"]
    record = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=utcnow() + expires_delta,
    )
    db.session.add(record)
    return raw_token


def get_valid_password_reset_token_record(raw_token: str):
    token_hash = hash_token(raw_token)
    record = PasswordResetToken.query.filter_by(token_hash=token_hash).first()
    if record is None or not record.is_valid(utcnow()):
        return None
    return record


def consume_password_reset_token(record: PasswordResetToken):
    record.used_at = utcnow()
