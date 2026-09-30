from datetime import datetime, timezone

from flask import current_app

from app.extensions import db, bcrypt
from app.models.user import User, UserRole, UserStatus
from app.models.audit_event import AuditEvent
from app.common.errors import (
    ConflictError,
    InvalidCredentialsError,
    AccountNotActiveError,
    NotFoundError,
    ValidationAppError,
)
from app.auth.tokens import (
    issue_access_token,
    issue_refresh_token,
    get_valid_refresh_token_record,
    revoke_refresh_token,
    revoke_all_refresh_tokens_for_user,
    issue_password_reset_token,
    get_valid_password_reset_token_record,
    consume_password_reset_token,
    utcnow,
)


def _record_audit_event(user_id, event_type, ip_address=None, user_agent=None):
    db.session.add(
        AuditEvent(
            user_id=user_id,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=(user_agent or "")[:255],
        )
    )


def register_user(data: dict, ip_address: str, user_agent: str) -> User:
    email = data["email"].strip().lower()
    phone = data["phone"].strip()

    if User.query.filter_by(email=email).first() is not None:
        raise ConflictError("An account with this email already exists.", code="EMAIL_TAKEN")
    if User.query.filter_by(phone=phone).first() is not None:
        raise ConflictError("An account with this phone number already exists.", code="PHONE_TAKEN")

    role = UserRole(data.get("role", UserRole.CUSTOMER.value))

    user = User(
        full_name=data["full_name"].strip(),
        email=email,
        phone=phone,
        password_hash=bcrypt.generate_hash(data["password"]),
        role=role,
        status=UserStatus.ACTIVE,
    )
    db.session.add(user)
    db.session.flush()  # obtain user.id for the audit event FK

    _record_audit_event(user.id, "USER_REGISTERED", ip_address, user_agent)
    db.session.commit()

    current_app.security_logger.registration(user.public_id, user.role.value, ip_address)
    return user


def authenticate_user(identifier: str, password: str, ip_address: str, user_agent: str) -> User:
    identifier_norm = identifier.strip().lower()
    user = User.query.filter(
        (User.email == identifier_norm) | (User.phone == identifier.strip())
    ).first()

    if user is None or not bcrypt.verify(password, user.password_hash):
        # Deliberately identical error/message whether the account exists or
        # not, so the response never discloses account existence.
        _record_audit_event(None, "LOGIN_FAILURE", ip_address, user_agent)
        db.session.commit()
        current_app.security_logger.login_failure(_mask(identifier), ip_address, "invalid_credentials")
        raise InvalidCredentialsError()

    if not user.is_active:
        _record_audit_event(user.id, "LOGIN_BLOCKED_INACTIVE", ip_address, user_agent)
        db.session.commit()
        current_app.security_logger.login_failure(_mask(identifier), ip_address, f"account_{user.status.value.lower()}")
        raise AccountNotActiveError(f"This account is {user.status.value.lower()}.")

    user.last_login_at = datetime.now(timezone.utc)
    _record_audit_event(user.id, "LOGIN_SUCCESS", ip_address, user_agent)
    db.session.commit()
    current_app.security_logger.login_success(user.public_id, ip_address)
    return user


def issue_token_pair(user: User) -> dict:
    access_token = issue_access_token(user)
    refresh_token = issue_refresh_token(user)
    db.session.commit()
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "Bearer"}


def refresh_token_pair(raw_refresh_token: str, ip_address: str) -> dict:
    record = get_valid_refresh_token_record(raw_refresh_token)
    if record is None:
        raise InvalidCredentialsError("Refresh token is invalid or has expired.", code="INVALID_REFRESH_TOKEN")

    user = db.session.get(User, record.user_id)
    if user is None or not user.is_active:
        raise AccountNotActiveError()

    # Rotation: the old refresh token is revoked the instant a new one is
    # issued, so a stolen-but-already-used token cannot be replayed.
    revoke_refresh_token(record)
    access_token = issue_access_token(user)
    new_refresh_token = issue_refresh_token(user)
    db.session.commit()

    current_app.security_logger.token_refresh(user.public_id, ip_address)
    return {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "Bearer"}


def logout_user(raw_refresh_token: str, current_user_public_id: str, ip_address: str):
    record = get_valid_refresh_token_record(raw_refresh_token)
    if record is not None:
        revoke_refresh_token(record)
        db.session.commit()
    current_app.security_logger.logout(current_user_public_id, ip_address)


def request_password_reset(email: str, ip_address: str) -> str | None:
    """Returns the raw reset token ONLY so tests / local dev can exercise the
    flow without a real mail server. In production this value would be
    emailed to the user, never returned by the API (see routes.py)."""
    email_norm = email.strip().lower()
    user = User.query.filter_by(email=email_norm).first()
    current_app.security_logger.password_reset_requested(_mask(email), ip_address)

    if user is None or not user.is_active:
        # Same response regardless of whether the account exists, to avoid
        # leaking account existence via timing or response shape.
        return None

    raw_token = issue_password_reset_token(user)
    db.session.commit()
    return raw_token


def complete_password_reset(raw_token: str, new_password: str, ip_address: str):
    record = get_valid_password_reset_token_record(raw_token)
    if record is None:
        raise ValidationAppError("This password reset link is invalid or has expired.", code="INVALID_RESET_TOKEN")

    user = db.session.get(User, record.user_id)
    if user is None:
        raise NotFoundError("Account not found.")

    user.password_hash = bcrypt.generate_hash(new_password)
    consume_password_reset_token(record)
    revoke_all_refresh_tokens_for_user(user)  # force re-login everywhere
    _record_audit_event(user.id, "PASSWORD_RESET_COMPLETED", ip_address, None)
    db.session.commit()

    current_app.security_logger.password_reset_completed(user.public_id, ip_address)


def _mask(identifier: str) -> str:
    """Reduces an email/phone to a low-detail hint for security logs, so logs
    are useful for detecting brute-force patterns without becoming a second
    copy of the user's contact information."""
    if "@" in identifier:
        local, _, domain = identifier.partition("@")
        return f"{local[:2]}***@{domain}"
    return f"***{identifier[-4:]}" if len(identifier) >= 4 else "***"
