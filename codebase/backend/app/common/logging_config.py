"""
Structured application logging.

Two loggers are configured:
  - "app"          general application logs
  - "app.security" security-relevant events (registration, login,
                    logout, password reset, authorization failures)

Neither logger is ever passed passwords, access tokens, refresh tokens, or
other secrets - only identifiers (user public_id, email) and event metadata
(IP, user-agent, outcome).
"""
import logging
import sys


class SecurityEventLogger:
    """Small helper so call sites read like `security_logger.login_success(...)`
    instead of hand-building log strings everywhere, which keeps sensitive
    fields from accidentally slipping into a log call."""

    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def _emit(self, event: str, **fields):
        safe_fields = ", ".join(f"{k}={v}" for k, v in fields.items())
        self._logger.info("event=%s %s", event, safe_fields)

    def registration(self, user_public_id, role, ip):
        self._emit("user_registered", user_public_id=user_public_id, role=role, ip=ip)

    def login_success(self, user_public_id, ip):
        self._emit("login_success", user_public_id=user_public_id, ip=ip)

    def login_failure(self, identifier_hint, ip, reason):
        self._emit("login_failure", identifier_hint=identifier_hint, ip=ip, reason=reason)

    def logout(self, user_public_id, ip):
        self._emit("logout", user_public_id=user_public_id, ip=ip)

    def token_refresh(self, user_public_id, ip):
        self._emit("token_refresh", user_public_id=user_public_id, ip=ip)

    def password_reset_requested(self, identifier_hint, ip):
        self._emit("password_reset_requested", identifier_hint=identifier_hint, ip=ip)

    def password_reset_completed(self, user_public_id, ip):
        self._emit("password_reset_completed", user_public_id=user_public_id, ip=ip)

    def authorization_failure(self, user_public_id, required_role, ip, path):
        self._emit(
            "authorization_failure",
            user_public_id=user_public_id,
            required_role=required_role,
            ip=ip,
            path=path,
        )

    def unexpected_error(self, ip, path):
        self._emit("unexpected_error", ip=ip, path=path)


def configure_logging(app):
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s level=%(levelname)s logger=%(name)s %(message)s"
    )
    handler.setFormatter(formatter)

    app_logger = logging.getLogger("app")
    app_logger.setLevel(logging.DEBUG if app.config.get("DEBUG") else logging.INFO)
    app_logger.addHandler(handler)
    app_logger.propagate = False

    security_logger = logging.getLogger("app.security")
    security_logger.setLevel(logging.INFO)
    security_logger.addHandler(handler)
    security_logger.propagate = False

    app.security_logger = SecurityEventLogger(security_logger)
    return app
