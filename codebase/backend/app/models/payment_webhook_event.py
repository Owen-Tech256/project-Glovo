import enum

from app.extensions import db
from app.models.base import PublicIdMixin, _utcnow


class WebhookProcessingStatus(str, enum.Enum):
    PROCESSED = "PROCESSED"
    IGNORED = "IGNORED"
    REJECTED = "REJECTED"


class PaymentWebhookEvent(db.Model, PublicIdMixin):
    """Durable record of every inbound provider webhook call, keyed by the
    provider's own event ID (SRS 6: "Deduplicate webhook events... use
    idempotency keys"). The unique constraint on (provider,
    external_event_id) is what makes duplicate delivery harmless: a second
    delivery of the same event hits the constraint, is recognized as a
    replay, and is never reprocessed - see
    app/payments/payment_service.py:process_webhook_event.

    Rejected (bad-signature) events are still stored, for audit, but never
    trigger any financial side effect.
    """

    __tablename__ = "payment_webhook_events"

    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(32), nullable=False, index=True)
    external_event_id = db.Column(db.String(255), nullable=False)
    event_type = db.Column(db.String(64), nullable=True)
    signature_verified = db.Column(db.Boolean, nullable=False, default=False)
    # A reference to the raw payload rather than the payload itself - this
    # phase stores a truncated JSON copy inline (no object storage exists
    # yet); a production deployment would point this at blob storage.
    payload_reference = db.Column(db.Text, nullable=True)
    processing_status = db.Column(
        db.Enum(WebhookProcessingStatus, name="webhook_processing_status", native_enum=False, length=20),
        nullable=False,
        index=True,
    )
    payment_id = db.Column(db.Integer, db.ForeignKey("payments.id", ondelete="SET NULL"), nullable=True, index=True)
    processed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)

    payment = db.relationship("Payment")

    __table_args__ = (
        db.UniqueConstraint("provider", "external_event_id", name="uq_webhook_events_provider_external_id"),
    )

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "provider": self.provider,
            "external_event_id": self.external_event_id,
            "event_type": self.event_type,
            "signature_verified": self.signature_verified,
            "processing_status": self.processing_status.value
            if isinstance(self.processing_status, WebhookProcessingStatus) else self.processing_status,
            "payment_id": self.payment.public_id if self.payment else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<PaymentWebhookEvent {self.provider}:{self.external_event_id} {self.processing_status}>"
