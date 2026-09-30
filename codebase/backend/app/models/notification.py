"""
One in-app notification-center entry per (recipient, event) - always
created regardless of the recipient's channel preferences, since this row
*is* the in-app inbox itself (SRS 7's IN_APP channel). Preferences instead
govern whether an accompanying EMAIL/SMS/PUSH NotificationDelivery is
attempted - see app/notifications/service.py.
"""
import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class NotificationCategory(str, enum.Enum):
    ORDER = "ORDER"
    PAYMENT = "PAYMENT"
    DELIVERY = "DELIVERY"
    PROMOTION = "PROMOTION"
    REVIEW = "REVIEW"
    PAYOUT = "PAYOUT"
    ADVERTISING = "ADVERTISING"
    ACCOUNT = "ACCOUNT"
    # Phase 7: ticket/dispute lifecycle events (agent reply, resolution,
    # dispute decision) - see app/support/service.py and
    # app/disputes/service.py.
    SUPPORT = "SUPPORT"
    DISPUTE = "DISPUTE"


class Notification(db.Model, PublicIdMixin, TimestampMixin):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    recipient_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category = db.Column(
        db.Enum(NotificationCategory, name="notification_category", native_enum=False, length=20), nullable=False, index=True
    )
    template_key = db.Column(db.String(80), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    # What this notification is about, so the frontend can deep-link (e.g.
    # entity_type="ORDER", entity_id=<order public_id>). Deliberately loose
    # (no FK) - the referenced row may later be deleted, and the
    # notification should still render.
    entity_type = db.Column(db.String(30), nullable=True)
    entity_id = db.Column(db.String(36), nullable=True)
    read_at = db.Column(db.DateTime(timezone=True), nullable=True)

    deliveries = db.relationship(
        "NotificationDelivery", backref="notification", lazy="dynamic", cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.Index("ix_notifications_recipient_read", "recipient_user_id", "read_at"),
        db.Index("ix_notifications_recipient_created", "recipient_user_id", "created_at"),
    )

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "category": self.category.value if isinstance(self.category, NotificationCategory) else self.category,
            "title": self.title,
            "body": self.body,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "is_read": self.read_at is not None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<Notification {self.public_id} {self.category} recipient={self.recipient_user_id}>"


class NotificationPreference(db.Model, TimestampMixin):
    """One row per (user, category, channel) the user has explicitly
    turned off. Absence of a row means enabled (SRS 7: "default sensible
    preferences") - see app/notifications/service.py:is_enabled. IN_APP is
    always delivered regardless of any row here (it's the inbox itself);
    preferences only gate EMAIL/SMS/PUSH."""

    __tablename__ = "notification_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category = db.Column(
        db.Enum(NotificationCategory, name="notification_category", native_enum=False, length=20), nullable=False
    )
    channel = db.Column(
        db.Enum("EMAIL", "SMS", "PUSH", name="notification_preference_channel", native_enum=False, length=10),
        nullable=False,
    )
    enabled = db.Column(db.Boolean, nullable=False, default=True)

    __table_args__ = (
        db.UniqueConstraint("user_id", "category", "channel", name="uq_notification_preferences_identity"),
    )

    def to_public_dict(self) -> dict:
        return {
            "category": self.category.value if isinstance(self.category, NotificationCategory) else self.category,
            "channel": self.channel,
            "enabled": self.enabled,
        }

    def __repr__(self):  # pragma: no cover
        return f"<NotificationPreference user_id={self.user_id} {self.category}:{self.channel}={self.enabled}>"
