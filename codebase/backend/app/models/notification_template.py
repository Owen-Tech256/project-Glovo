"""
Admin-managed content templates for notifications (SRS 7: "Support
templated messages with variable substitution"). One (key, channel) pair
per template - e.g. ("order_confirmed", "IN_APP") and
("order_confirmed", "EMAIL") are two separate rows, since wording and even
whether a channel fires at all can differ per channel. `version` increments
on every edit (SRS 7: "template versioning"); this phase keeps only the
current version in place rather than a full history table, which is a
documented scope reduction - see PHASE_6_NOTES.md.
"""
import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class NotificationChannel(str, enum.Enum):
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"


class NotificationTemplateStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class NotificationTemplate(db.Model, PublicIdMixin, TimestampMixin):
    __tablename__ = "notification_templates"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), nullable=False, index=True)
    channel = db.Column(
        db.Enum(NotificationChannel, name="notification_channel", native_enum=False, length=10), nullable=False, index=True
    )
    category = db.Column(db.String(30), nullable=False)
    # Rendered with str.format(**context) by app/notifications/service.py -
    # e.g. "Your order {order_number} has been confirmed."
    title_template = db.Column(db.String(200), nullable=False)
    body_template = db.Column(db.Text, nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(
        db.Enum(NotificationTemplateStatus, name="notification_template_status", native_enum=False, length=10),
        nullable=False, default=NotificationTemplateStatus.ACTIVE,
    )

    __table_args__ = (
        db.UniqueConstraint("key", "channel", name="uq_notification_templates_key_channel"),
    )

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "key": self.key,
            "channel": self.channel.value if isinstance(self.channel, NotificationChannel) else self.channel,
            "category": self.category,
            "title_template": self.title_template,
            "body_template": self.body_template,
            "version": self.version,
            "status": self.status.value if isinstance(self.status, NotificationTemplateStatus) else self.status,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<NotificationTemplate {self.key}:{self.channel}>"
