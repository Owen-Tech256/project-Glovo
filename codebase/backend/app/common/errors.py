"""
Custom application exceptions and their registration with Flask's error
handling system. Every exception here maps to a stable machine-readable
`code` and an appropriate HTTP status. Handlers never leak internal
exception details (stack traces, SQL errors, etc.) to the client.
"""
import logging

from flask import current_app
from marshmallow import ValidationError as MarshmallowValidationError
from werkzeug.exceptions import HTTPException

from app.common.responses import error

logger = logging.getLogger("app")


class AppError(Exception):
    """Base class for all application-raised, client-facing errors."""

    code = "APP_ERROR"
    status_code = 400
    message = "An error occurred."

    def __init__(self, message: str | None = None, code: str | None = None,
                 status_code: int | None = None, details=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.details = details


class ValidationAppError(AppError):
    code = "VALIDATION_ERROR"
    status_code = 422
    message = "The submitted data is invalid."


class AuthenticationError(AppError):
    code = "UNAUTHENTICATED"
    status_code = 401
    message = "Authentication is required."


class InvalidCredentialsError(AppError):
    code = "INVALID_CREDENTIALS"
    status_code = 401
    message = "Invalid email/phone or password."


class AuthorizationError(AppError):
    code = "FORBIDDEN"
    status_code = 403
    message = "You do not have permission to perform this action."


class AccountNotActiveError(AppError):
    code = "ACCOUNT_NOT_ACTIVE"
    status_code = 403
    message = "This account is not active."


class NotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = 404
    message = "The requested resource was not found."


class ConflictError(AppError):
    code = "CONFLICT"
    status_code = 409
    message = "The resource already exists."


class RateLimitedError(AppError):
    code = "RATE_LIMITED"
    status_code = 429
    message = "Too many requests. Please try again later."


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(exc: AppError):
        return error(exc.code, exc.message, exc.status_code, getattr(exc, "details", None))

    @app.errorhandler(MarshmallowValidationError)
    def handle_marshmallow_error(exc: MarshmallowValidationError):
        return error("VALIDATION_ERROR", "The submitted data is invalid.", 422, exc.messages)

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHENTICATED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
            422: "VALIDATION_ERROR",
            429: "RATE_LIMITED",
        }
        code = code_map.get(exc.code, "HTTP_ERROR")
        return error(code, exc.description or exc.name, exc.code or 500)

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc: Exception):
        # Never leak internal exception details to the client. Log the full
        # exception server-side for debugging.
        logger.exception("Unhandled exception: %s", exc)
        if current_app.config.get("DEBUG"):
            # In local development it is useful to see what broke, but this
            # branch must never be reachable in production (DEBUG=False).
            return error("INTERNAL_ERROR", str(exc), 500)
        return error("INTERNAL_ERROR", "An unexpected error occurred.", 500)
