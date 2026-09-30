"""
Application configuration.

Configuration is intentionally kept separate from application code so that
secrets and environment-specific values never live in source control.
Populate a local `.env` file (see `.env.example`) for development.
"""
import os
from datetime import timedelta

from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(basedir, ".env"))


def _split_origins(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


class BaseConfig:
    """Shared configuration across all environments."""

    # --- Core Flask ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    JSON_SORT_KEYS = False

    # --- SQLAlchemy ---
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # --- JWT ---
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES_SECONDS", 900))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        seconds=int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRES_SECONDS", 1209600))
    )
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_TYPE = "Bearer"
    JWT_ERROR_MESSAGE_KEY = "message"

    # --- CORS ---
    CORS_ORIGINS = _split_origins(os.environ.get("CORS_ORIGINS", "http://localhost:5173"))

    # --- Rate limiting ---
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_DEFAULT = "200 per hour"

    # --- App-specific ---
    BCRYPT_LOG_ROUNDS = int(os.environ.get("BCRYPT_LOG_ROUNDS", 12))
    PASSWORD_RESET_TOKEN_EXPIRES = timedelta(minutes=30)

    # --- Phase 3: cart / checkout ---
    # Configurable per-line quantity ceiling (SRS 6.1: "subject to configurable
    # maximum limits"). Kept as a single global default rather than a
    # per-product override, which is out of scope for this phase.
    CART_MAX_ITEM_QUANTITY = int(os.environ.get("CART_MAX_ITEM_QUANTITY", 20))
    # Flat delivery/service fee applied at checkout. Phase 3 has no fee engine
    # (dynamic pricing, distance-based fees, promotions) - a single
    # configurable flat fee is the documented placeholder; see the Phase 3
    # assumptions note in the backend README.
    DELIVERY_FEE_FLAT = os.environ.get("DELIVERY_FEE_FLAT", "2.99")

    # --- Phase 4: logistics ---
    # A rider's last reported position older than this is "stale" and
    # excludes them from dispatch (SRS 7/8) and from customer tracking
    # (SRS 9's "stale-location feedback").
    RIDER_LOCATION_FRESHNESS_SECONDS = int(os.environ.get("RIDER_LOCATION_FRESHNESS_SECONDS", 120))
    # Application-level floor between two accepted location pings from the
    # same rider, enforced in app/logistics/rider_service.py regardless of
    # the IP-based RATELIMIT_* throttling on the route itself (which is
    # disabled in the test suite - see TestingConfig below).
    RIDER_LOCATION_MIN_INTERVAL_SECONDS = int(os.environ.get("RIDER_LOCATION_MIN_INTERVAL_SECONDS", 3))
    # How long a single dispatch offer stays claimable before it expires and
    # the delivery is redispatched to the next candidates (SRS 8).
    DELIVERY_OFFER_EXPIRY_SECONDS = int(os.environ.get("DELIVERY_OFFER_EXPIRY_SECONDS", 45))
    # How many top-ranked eligible riders are offered a delivery at once.
    # >1 is what gives "prevent two riders from claiming one delivery"
    # (SRS 8) real teeth - see app/logistics/dispatch_service.py.
    DISPATCH_OFFER_BATCH_SIZE = int(os.environ.get("DISPATCH_OFFER_BATCH_SIZE", 3))
    # A hard ceiling on how many candidates dispatch will ever rank/consider
    # for one delivery, independent of how many riders are online, to keep
    # the ranking query bounded.
    DISPATCH_MAX_CANDIDATES = int(os.environ.get("DISPATCH_MAX_CANDIDATES", 50))
    # Phase 9: how long a delivery may sit in SEARCHING/OFFERED before the
    # admin dispatch-health view flags it as stuck - see
    # app/logistics/admin_service.py:get_dispatch_health. Status visibility
    # only; not itself a dispatch behavior control.
    DISPATCH_STUCK_THRESHOLD_SECONDS = int(os.environ.get("DISPATCH_STUCK_THRESHOLD_SECONDS", 180))

    # --- Phase 5: money (payments / commissions / wallets / payouts) ---
    # Single-currency platform. Multi-currency settlement is explicitly out
    # of scope (SRS 3) - every Phase 5 monetary row still stores this
    # explicitly per amount, as required, rather than assuming it globally.
    DEFAULT_CURRENCY = os.environ.get("DEFAULT_CURRENCY", "USD")
    # Which registered provider adapter (see app/payments/providers/) new
    # payments/refunds/payouts use when the caller doesn't name one.
    DEFAULT_PAYMENT_PROVIDER = os.environ.get("DEFAULT_PAYMENT_PROVIDER", "mock")
    # Shared secret the mock provider signs webhook payloads with (HMAC
    # SHA-256) and verifies incoming webhook calls against. A real adapter
    # would instead hold the gateway's own signing secret.
    MOCK_PROVIDER_WEBHOOK_SECRET = os.environ.get("MOCK_PROVIDER_WEBHOOK_SECRET", "dev-webhook-secret-change-me")
    # Bootstrap platform commission applied when no admin-configured
    # CommissionRule exists yet, so settlement never fails on an unconfigured
    # marketplace (see app/payments/commission_service.py). An admin can
    # supersede this at any time via POST /admin/commission-rules.
    PLATFORM_COMMISSION_PERCENTAGE_DEFAULT = os.environ.get("PLATFORM_COMMISSION_PERCENTAGE_DEFAULT", "0.15")
    # Whether a customer refund request needs explicit admin approval before
    # it is sent to the provider (SRS 10: "Support configured approval
    # rules"). False auto-approves and processes immediately on request.
    REFUND_REQUIRES_APPROVAL = os.environ.get("REFUND_REQUIRES_APPROVAL", "true").lower() == "true"

    # --- Phase 6: growth & engagement (promotions / advertising / reviews / notifications) ---
    # Whether product-level reviews (in addition to vendor/rider reviews)
    # are accepted - an admin-configurable toggle per SRS 6's "may be
    # enabled depending on business rules".
    PRODUCT_REVIEWS_ENABLED = os.environ.get("PRODUCT_REVIEWS_ENABLED", "true").lower() == "true"
    # Whether a newly created ad campaign must be admin-approved
    # (PENDING_REVIEW -> ACTIVE) before it can serve/bill events, or goes
    # straight to ACTIVE on creation (SRS 5: "Support admin moderation of
    # ad content before it goes live").
    AD_CAMPAIGN_REQUIRES_APPROVAL = os.environ.get("AD_CAMPAIGN_REQUIRES_APPROVAL", "true").lower() == "true"
    # Which registered notification provider adapter (see
    # app/notifications/providers/) EMAIL/SMS/PUSH deliveries use.
    NOTIFICATION_PROVIDER = os.environ.get("NOTIFICATION_PROVIDER", "console")


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://delivery_user:delivery_pass@localhost:5432/delivery_marketplace",
    )


class TestingConfig(BaseConfig):
    """Used by the automated test suite. Runs on an in-memory SQLite DB so
    the suite has no external Postgres dependency, while application code
    still targets Postgres-compatible SQLAlchemy/ORM usage only."""

    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")
    BCRYPT_LOG_ROUNDS = 4  # fast hashing in tests
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=30)
    RATELIMIT_ENABLED = False


class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")

    @staticmethod
    def validate():
        """Called explicitly from the app factory (not __init__, since Flask
        uses these classes without instantiating them)."""
        if not os.environ.get("DATABASE_URL"):
            raise RuntimeError("DATABASE_URL must be set in production")
        if os.environ.get("SECRET_KEY", "dev-secret-key-change-me") == "dev-secret-key-change-me":
            raise RuntimeError("SECRET_KEY must be overridden in production")
        if os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-change-me") == "dev-jwt-secret-change-me":
            raise RuntimeError("JWT_SECRET_KEY must be overridden in production")


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
