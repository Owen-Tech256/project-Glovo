import json

from app.extensions import db
from app.models.base import _utcnow


class AuditEvent(db.Model):
    """Append-only audit trail. `user_id` is nullable so system/anonymous
    events (e.g. a failed login for an email that doesn't exist) can still
    be recorded without fabricating a user reference.

    Phase 7 extends this Phase 1 table in place rather than standing up a
    second, parallel audit table: the SRS 11 ER diagram already models
    `USER 1:N AUDIT_EVENT`, and `event_type` is exactly SRS 12's `action`
    column by another name - every existing call site (auth/service.py,
    logistics/admin_service.py, payments/admin_finance_service.py) keeps
    working unchanged against the same table. `entity_type`/`entity_id`/
    `before_data`/`after_data`/`event_metadata` are new, all nullable, so
    the pre-Phase-7 rows and call sites are unaffected. `event_metadata`
    (not `metadata`) because `metadata` is reserved on `db.Model`.
    before_data/after_data/event_metadata are stored as JSON-serialized
    text, the same "structured data in a Text column" approach already
    used for `DeliveryZone.polygon_geojson` elsewhere in this codebase,
    rather than a JSON column type (kept portable across the SQLite test
    backend and Postgres)."""

    __tablename__ = "audit_events"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = db.Column(db.String(64), nullable=False, index=True)
    ip_address = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)

    entity_type = db.Column(db.String(64), nullable=True, index=True)
    entity_id = db.Column(db.String(64), nullable=True, index=True)
    before_data = db.Column(db.Text, nullable=True)
    after_data = db.Column(db.Text, nullable=True)
    event_metadata = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)

    __table_args__ = (
        db.Index("ix_audit_events_entity", "entity_type", "entity_id"),
    )

    def to_public_dict(self) -> dict:
        def _parse(raw):
            if raw is None:
                return None
            try:
                return json.loads(raw)
            except (TypeError, ValueError):
                return raw

        return {
            "id": self.id,
            "actor": {"id": self.user.public_id, "name": self.user.full_name} if self.user else None,
            "action": self.event_type,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "before": _parse(self.before_data),
            "after": _parse(self.after_data),
            "metadata": _parse(self.event_metadata),
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<AuditEvent {self.event_type} user_id={self.user_id}>"
