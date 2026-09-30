from app.extensions import db
from app.models.base import TimestampMixin, to_aware_utc


class RefreshToken(db.Model, TimestampMixin):
    """Stores only a hash of each issued refresh token, never the raw value.
    Enables server-side revocation (logout, password reset, admin action)
    and rotation (a refresh call revokes the old token and issues a new one).
    """

    __tablename__ = "refresh_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = db.Column(db.String(255), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    revoked_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def is_valid(self, now) -> bool:
        return self.revoked_at is None and to_aware_utc(self.expires_at) > to_aware_utc(now)
