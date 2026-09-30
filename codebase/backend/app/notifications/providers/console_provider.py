"""
The only adapter this phase ships (SRS 7 lists external email/SMS/push
gateways as out of scope for the core build - see PHASE_6_NOTES.md). It
"delivers" by logging and always succeeds, the same role
app/payments/providers/mock_provider.py plays for payments - it proves the
abstraction (NotificationDelivery rows, attempt tracking, failure
handling) works end-to-end without a real gateway credential.
"""
import logging
import uuid

from app.notifications.providers.base import NotificationProviderAdapter, DeliveryResult

logger = logging.getLogger("app.notifications")


class ConsoleProviderAdapter(NotificationProviderAdapter):
    name = "console"

    def _send(self, channel: str, recipient_user, title: str, body: str) -> DeliveryResult:
        reference = f"console_{channel.lower()}_{uuid.uuid4().hex[:12]}"
        logger.info("[notification:%s] to user=%s :: %s — %s", channel, recipient_user.public_id, title, body)
        return DeliveryResult(status="SENT", provider_reference=reference)

    def send_email(self, recipient_user, title: str, body: str) -> DeliveryResult:
        return self._send("EMAIL", recipient_user, title, body)

    def send_sms(self, recipient_user, title: str, body: str) -> DeliveryResult:
        return self._send("SMS", recipient_user, title, body)

    def send_push(self, recipient_user, title: str, body: str) -> DeliveryResult:
        return self._send("PUSH", recipient_user, title, body)
