"""
The single reusable audit-recording entry point for Phase 7 (implementation
prompt 6: "Create a reusable audit service"). Every privileged Phase 7
action (role changes, dispute financial actions, ticket assignment/
resolution, admin user-status changes, RBAC changes, config changes)
should call `record()` rather than constructing an AuditEvent directly.

`record()` never raises - like app/notifications/events.py:notify(), a
failure to write an audit row must never block or roll back the business
action it is describing. It logs and swallows instead.

Before/after values are the caller's responsibility to keep "safe" (SRS
10/implementation prompt 6: "Never store passwords, tokens, payment
credentials or secrets") - this module does not attempt to redact
arbitrary dicts, since a generic redaction pass over unknown keys is
easy to get wrong in a way that hides a real omission. Callers pass only
the specific, already-safe fields they mean to record (e.g. `{"status":
"SUSPENDED"}`, never a whole User row).
"""
import json
import logging

from app.extensions import db
from app.models.audit_event import AuditEvent

logger = logging.getLogger("app.audit")


def record(actor, action: str, entity_type: str | None = None, entity_id: str | None = None,
           before: dict | None = None, after: dict | None = None, metadata: dict | None = None,
           ip_address: str | None = None, user_agent: str | None = None) -> None:
    try:
        event = AuditEvent(
            user_id=actor.id if actor is not None else None,
            event_type=action,
            ip_address=ip_address,
            user_agent=(user_agent or "")[:255] or None,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            before_data=json.dumps(before, default=str) if before is not None else None,
            after_data=json.dumps(after, default=str) if after is not None else None,
            event_metadata=json.dumps(metadata, default=str) if metadata is not None else None,
        )
        db.session.add(event)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Failed to record audit event action=%s entity_type=%s entity_id=%s", action, entity_type, entity_id)


def list_events(entity_type: str | None = None, entity_id: str | None = None, user_public_id: str | None = None,
                 action: str | None = None, page: int = 1, per_page: int = 20):
    query = AuditEvent.query
    if entity_type:
        query = query.filter(AuditEvent.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditEvent.entity_id == str(entity_id))
    if action:
        query = query.filter(AuditEvent.event_type == action)
    if user_public_id:
        from app.models.user import User

        user = User.query.filter_by(public_id=user_public_id).first()
        query = query.filter(AuditEvent.user_id == (user.id if user else -1))
    return query.order_by(AuditEvent.created_at.desc()).paginate(
        page=max(page, 1), per_page=max(min(per_page, 100), 1), error_out=False
    )
