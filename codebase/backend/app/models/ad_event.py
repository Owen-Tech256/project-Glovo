"""
Billable ad interactions (SRS 5: "Track impressions and clicks... prevent
fraudulent or duplicate ad interaction counts"). `event_reference` is a
client-supplied idempotency key (e.g. one per impression render) unique per
campaign, so a retried/double-fired tracking beacon never double-bills a
vendor's budget - see app/advertising/service.py:record_event.
"""
import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class AdEventType(str, enum.Enum):
    IMPRESSION = "IMPRESSION"
    CLICK = "CLICK"


class AdEvent(db.Model, PublicIdMixin, TimestampMixin):
    __tablename__ = "ad_events"

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("ad_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = db.Column(db.Enum(AdEventType, name="ad_event_type", native_enum=False, length=20), nullable=False, index=True)
    viewer_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event_reference = db.Column(db.String(128), nullable=True)
    billed_amount = db.Column(db.Numeric(10, 4), nullable=False, default=0)
    occurred_at = db.Column(db.DateTime(timezone=True), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("campaign_id", "event_reference", name="uq_ad_events_campaign_reference"),
        db.Index("ix_ad_events_campaign_type", "campaign_id", "event_type"),
    )

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "event_type": self.event_type.value if isinstance(self.event_type, AdEventType) else self.event_type,
            "billed_amount": str(self.billed_amount),
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<AdEvent campaign_id={self.campaign_id} {self.event_type}>"
