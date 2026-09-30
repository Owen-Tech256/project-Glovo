"""
Notification creation, dispatch, and inbox management (SRS 7).

`create_notification` always writes the IN_APP Notification row (that row
*is* the in-app inbox), then separately - and best-effort - attempts an
EMAIL/SMS/PUSH NotificationDelivery for any channel that (a) has its own
ACTIVE NotificationTemplate for this key and (b) the recipient hasn't
turned off for this category. A delivery failure is recorded on its own
NotificationDelivery row and never raised - see the module-level try/except
in app/notifications/events.py, which is the only way any other service in
this codebase is meant to reach this module.
"""
import logging

from app.extensions import db
from app.common.errors import NotFoundError
from app.models.notification import Notification, NotificationCategory, NotificationPreference
from app.models.notification_delivery import NotificationDelivery, NotificationDeliveryStatus
from app.models.notification_template import NotificationTemplate, NotificationChannel, NotificationTemplateStatus
from app.notifications.templates import get_or_create_template
from app.notifications.providers import get_provider

logger = logging.getLogger("app.notifications")

_OFF_APP_CHANNELS = (NotificationChannel.EMAIL, NotificationChannel.SMS, NotificationChannel.PUSH)


def is_enabled(user_id: int, category: NotificationCategory, channel: str) -> bool:
    """Absence of a NotificationPreference row means enabled (SRS 7:
    "default sensible preferences") - a user only ever has a row here for
    something they've explicitly turned *off*."""
    pref = NotificationPreference.query.filter_by(user_id=user_id, category=category, channel=channel).first()
    return pref is None or pref.enabled


def _render(template: NotificationTemplate, context: dict) -> tuple[str, str]:
    try:
        title = template.title_template.format(**context)
        body = template.body_template.format(**context)
    except (KeyError, IndexError):
        # A template referencing a context key the caller didn't supply is
        # an admin content-authoring mistake, not a reason to break the
        # business event that triggered this notification - fall back to
        # the unrendered template text.
        logger.warning("Notification template %s missing context key for %s", template.key, context)
        title, body = template.title_template, template.body_template
    return title, body


def create_notification(
    recipient_user, category: NotificationCategory, title: str | None = None, body: str | None = None,
    template_key: str | None = None, context: dict | None = None,
    entity_type: str | None = None, entity_id: str | None = None,
) -> Notification:
    context = context or {}
    resolved_title, resolved_body = title, body

    if template_key:
        in_app_template = get_or_create_template(template_key)
        if in_app_template is not None:
            resolved_title, resolved_body = _render(in_app_template, context)
            category = NotificationCategory(in_app_template.category)

    notification = Notification(
        recipient_user_id=recipient_user.id, category=category, template_key=template_key,
        title=resolved_title or "Notification", body=resolved_body or "",
        entity_type=entity_type, entity_id=entity_id,
    )
    db.session.add(notification)
    db.session.flush()

    if template_key:
        for channel in _OFF_APP_CHANNELS:
            if not is_enabled(recipient_user.id, category, channel.value):
                continue
            channel_template = NotificationTemplate.query.filter_by(
                key=template_key, channel=channel, status=NotificationTemplateStatus.ACTIVE
            ).first()
            if channel_template is None:
                continue
            _dispatch(notification, recipient_user, channel_template, context)

    db.session.commit()
    return notification


def _dispatch(notification: Notification, recipient_user, template: NotificationTemplate, context: dict) -> NotificationDelivery:
    title, body = _render(template, context)
    delivery = NotificationDelivery(
        notification_id=notification.id, channel=template.channel.value, attempt_count=1,
    )
    db.session.add(delivery)
    provider = get_provider()
    method = {"EMAIL": provider.send_email, "SMS": provider.send_sms, "PUSH": provider.send_push}[template.channel.value]
    result = method(recipient_user, title, body)
    delivery.provider = provider.name
    if result.status == "SENT":
        delivery.status = NotificationDeliveryStatus.SENT
        delivery.provider_reference = result.provider_reference
        from app.payments.ledger_service import utcnow

        delivery.delivered_at = utcnow()
    else:
        delivery.status = NotificationDeliveryStatus.FAILED
        delivery.failure_reason = result.failure_reason
    return delivery


# --- Inbox -----------------------------------------------------------------

def list_notifications(user, unread_only: bool = False, page: int = 1, per_page: int = 20):
    query = Notification.query.filter_by(recipient_user_id=user.id)
    if unread_only:
        query = query.filter(Notification.read_at.is_(None))
    return query.order_by(Notification.created_at.desc()).paginate(
        page=max(page, 1), per_page=max(min(per_page, 100), 1), error_out=False
    )


def unread_count(user) -> int:
    return Notification.query.filter_by(recipient_user_id=user.id, read_at=None).count()


def mark_read(user, notification_public_id: str) -> Notification:
    notification = Notification.query.filter_by(public_id=notification_public_id, recipient_user_id=user.id).first()
    if notification is None:
        raise NotFoundError("Notification not found.")
    if notification.read_at is None:
        from app.payments.ledger_service import utcnow

        notification.read_at = utcnow()
        db.session.commit()
    return notification


def mark_all_read(user) -> int:
    from app.payments.ledger_service import utcnow

    updated = Notification.query.filter_by(recipient_user_id=user.id, read_at=None).update(
        {"read_at": utcnow()}, synchronize_session=False
    )
    db.session.commit()
    return updated


# --- Preferences -------------------------------------------------------

def get_preferences(user) -> list[NotificationPreference]:
    return NotificationPreference.query.filter_by(user_id=user.id).all()


def set_preference(user, category: str, channel: str, enabled: bool) -> NotificationPreference:
    category_enum = NotificationCategory(category)
    pref = NotificationPreference.query.filter_by(user_id=user.id, category=category_enum, channel=channel).first()
    if pref is None:
        pref = NotificationPreference(user_id=user.id, category=category_enum, channel=channel, enabled=enabled)
        db.session.add(pref)
    else:
        pref.enabled = enabled
    db.session.commit()
    return pref
