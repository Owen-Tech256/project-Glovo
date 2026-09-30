from app.extensions import db
from app.models.base import TimestampMixin, to_aware_utc


class PasswordResetToken(db.Model, TimestampMixin):
    """Stores only a hash of the reset token that was emailed/sent to the
    user, never the raw value. `used_at` prevents replay of a token after
    it has completed a reset."""

    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = db.Column(db.String(255), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def is_valid(self, now) -> bool:
        return self.used_at is None and to_aware_utc(self.expires_at) > to_aware_utc(now)
