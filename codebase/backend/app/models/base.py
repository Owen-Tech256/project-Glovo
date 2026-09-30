import uuid
from datetime import datetime, timezone

from app.extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


def to_aware_utc(dt):
    """SQLite (used in the test suite) drops timezone info on round-trip,
    while Postgres's TIMESTAMPTZ preserves it. Normalize here so expiry
    comparisons work identically against either backend."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )


class PublicIdMixin:
    """Exposes a non-sequential, non-guessable identifier to clients.
    The internal integer `id` is only ever used for foreign keys and joins,
    never returned by the API."""

    public_id = db.Column(
        db.String(36),
        unique=True,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
