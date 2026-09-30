from flask import current_app

from app.common.errors import ValidationAppError
from app.notifications.providers.base import NotificationProviderAdapter
from app.notifications.providers.console_provider import ConsoleProviderAdapter

_REGISTRY: dict[str, type[NotificationProviderAdapter]] = {
    "console": ConsoleProviderAdapter,
}


def get_provider(name: str | None = None) -> NotificationProviderAdapter:
    name = name or current_app.config.get("NOTIFICATION_PROVIDER", "console")
    provider_cls = _REGISTRY.get(name)
    if provider_cls is None:
        raise ValidationAppError(f"Unsupported notification provider: {name}.", code="UNSUPPORTED_PROVIDER")
    return provider_cls()
