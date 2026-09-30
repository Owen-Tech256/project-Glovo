"""
Provider adapter registry/factory. New adapters register themselves here;
every service in app/payments/ resolves a provider by name through
get_provider() rather than importing a concrete adapter class directly.
"""
from flask import current_app

from app.common.errors import ValidationAppError
from app.payments.providers.base import PaymentProviderAdapter
from app.payments.providers.mock_provider import MockProviderAdapter

_REGISTRY: dict[str, type[PaymentProviderAdapter]] = {
    "mock": MockProviderAdapter,
}


def get_provider(name: str | None = None) -> PaymentProviderAdapter:
    name = name or current_app.config.get("DEFAULT_PAYMENT_PROVIDER", "mock")
    provider_cls = _REGISTRY.get(name)
    if provider_cls is None:
        raise ValidationAppError(f"Unsupported payment provider: {name}.", code="UNSUPPORTED_PROVIDER")
    return provider_cls()
