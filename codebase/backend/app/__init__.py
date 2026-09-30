import os

from flask import Flask

from app.config import config_by_name
from app.extensions import db, migrate, jwt, cors, limiter, bcrypt
from app.common.errors import register_error_handlers
from app.common.logging_config import configure_logging


def create_app(config_name: str | None = None) -> Flask:
    config_name = config_name or os.environ.get("APP_CONFIG", "development")
    config_class = config_by_name[config_name]

    if hasattr(config_class, "validate"):
        config_class.validate()

    app = Flask(__name__)
    app.config.from_object(config_class)

    _init_extensions(app)
    configure_logging(app)
    register_error_handlers(app)

    from app.api import register_blueprints

    register_blueprints(app)

    _register_jwt_callbacks(app)

    @app.after_request
    def add_security_headers(response):
        # Baseline hardening headers. A production deployment behind a CDN
        # or reverse proxy would typically also set HSTS there.
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response

    return app


def _init_extensions(app: Flask):
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    limiter.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", [])}},
        supports_credentials=True,
    )
    # Import models so Flask-Migrate can discover them via metadata.
    from app import models  # noqa: F401


def _register_jwt_callbacks(app: Flask):
    from app.common.responses import error

    @jwt.unauthorized_loader
    def missing_token(reason):
        return error("UNAUTHENTICATED", "An access token is required.", 401)

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return error("UNAUTHENTICATED", "The access token is invalid.", 401)

    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_payload):
        return error("UNAUTHENTICATED", "The access token has expired.", 401)
