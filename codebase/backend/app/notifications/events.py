"""
The single call every other module in this codebase uses to fire a
notification (SRS 7: "must not make core order/payment operations depend
synchronously on an external notification provider"). `notify()` never
raises - a broken template, an unreachable provider, or any other failure
here is logged and swallowed so it can never roll back or block the
business transaction that just happened (a payment confirming, a delivery
completing, ...).

Every call site in this codebase invokes `notify()` *after* its own
business transaction has already committed - so this function safely runs
its own separate commit rather than trying to join a transaction that may
already be closed.
"""
import logging

from app.extensions import db
from app.models.notification import NotificationCategory

logger = logging.getLogger("app.notifications")


def notify(
    recipient_user, category: NotificationCategory, title: str | None = None, body: str | None = None,
    template_key: str | None = None, context: dict | None = None,
    entity_type: str | None = None, entity_id: str | None = None,
) -> None:
    if recipient_user is None:
        return
    try:
        from app.notifications.service import create_notification

        create_notification(
            recipient_user, category, title=title, body=body, template_key=template_key,
            context=context, entity_type=entity_type, entity_id=entity_id,
        )
    except Exception:
        db.session.rollback()
        logger.exception("Failed to create notification (template=%s) for user=%s", template_key, recipient_user.public_id)
