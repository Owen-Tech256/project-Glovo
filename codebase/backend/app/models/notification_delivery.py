"""
One attempted off-app delivery (EMAIL/SMS/PUSH) of a Notification, via
whichever provider adapter app/notifications/providers/ is configured for
that channel (SRS 7: "abstract provider integration... swappable without
major refactor" - the same adapter pattern app/payments/providers/ already
established). A failed delivery never rolls back or blocks the
Notification/business event it belongs to - see
app/notifications/service.py's module docstring.
"""
import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class NotificationDeliveryStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class NotificationDelivery(db.Model, PublicIdMixin, TimestampMixin):
    __tablename__ = "notification_deliveries"

    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(db.Integer, db.ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = db.Column(
        db.Enum("EMAIL", "SMS", "PUSH", name="notification_delivery_channel", native_enum=False, length=10),
        nullable=False,
    )
    provider = db.Column(db.String(50), nullable=False, default="console")
    status = db.Column(
        db.Enum(NotificationDeliveryStatus, name="notification_delivery_status", native_enum=False, length=10),
        nullable=False, default=NotificationDeliveryStatus.PENDING, index=True,
    )
    provider_reference = db.Column(db.String(255), nullable=True)
    attempt_count = db.Column(db.Integer, nullable=False, default=0)
    failure_reason = db.Column(db.String(500), nullable=True)
    delivered_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def to_public_dict(self) -> dict:
        return {
            "channel": self.channel,
            "status": self.status.value if isinstance(self.status, NotificationDeliveryStatus) else self.status,
            "attempt_count": self.attempt_count,
            "failure_reason": self.failure_reason,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<NotificationDelivery notification_id={self.notification_id} {self.channel} {self.status}>"
