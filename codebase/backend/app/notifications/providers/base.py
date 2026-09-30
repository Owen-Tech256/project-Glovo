"""
The notification provider adapter interface (SRS 7: "abstract provider
integration (e.g., for email/SMS) so it can be swapped without a major
refactor"). Mirrors app/payments/providers/base.py's shape exactly - one
small provider-agnostic result object, one method per off-app channel.
"""
from dataclasses import dataclass


@dataclass
class DeliveryResult:
    status: str  # "SENT" | "FAILED"
    provider_reference: str | None = None
    failure_reason: str | None = None


class NotificationProviderAdapter:
    name = "base"

    def send_email(self, recipient_user, title: str, body: str) -> DeliveryResult:
        raise NotImplementedError

    def send_sms(self, recipient_user, title: str, body: str) -> DeliveryResult:
        raise NotImplementedError

    def send_push(self, recipient_user, title: str, body: str) -> DeliveryResult:
        raise NotImplementedError
