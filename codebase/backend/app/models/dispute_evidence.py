from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class DisputeEvidence(db.Model, PublicIdMixin, TimestampMixin):
    """A submitted piece of evidence (photo, document, or free-text
    statement). `secure_reference` mirrors SupportAttachment/RiderDocument -
    a reference to where a file lives in real object storage, not the file
    itself (out of scope for this phase)."""

    __tablename__ = "dispute_evidence"

    id = db.Column(db.Integer, primary_key=True)
    dispute_id = db.Column(db.Integer, db.ForeignKey("disputes.id", ondelete="CASCADE"), nullable=False, index=True)
    submitted_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    evidence_type = db.Column(db.String(30), nullable=False)  # PHOTO / DOCUMENT / STATEMENT / OTHER
    secure_reference = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=True)

    submitter = db.relationship("User")

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "submitted_by": {"id": self.submitter.public_id, "name": self.submitter.full_name} if self.submitter else None,
            "evidence_type": self.evidence_type,
            "secure_reference": self.secure_reference,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<DisputeEvidence dispute_id={self.dispute_id} {self.evidence_type}>"
