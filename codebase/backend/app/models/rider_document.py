import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class RiderDocumentType(str, enum.Enum):
    GOVERNMENT_ID = "GOVERNMENT_ID"
    DRIVERS_LICENSE = "DRIVERS_LICENSE"
    VEHICLE_REGISTRATION = "VEHICLE_REGISTRATION"
    INSURANCE = "INSURANCE"
    BACKGROUND_CHECK = "BACKGROUND_CHECK"
    OTHER = "OTHER"


class RiderDocumentVerificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class RiderDocument(db.Model, PublicIdMixin, TimestampMixin):
    """A single submitted document. `reference` is a secure reference to
    where the file lives (an object-storage key/URL in production) -
    Phase 4 does not implement file upload/storage itself (out of scope),
    only the record-keeping and verification workflow around it."""

    __tablename__ = "rider_documents"

    id = db.Column(db.Integer, primary_key=True)
    rider_id = db.Column(db.Integer, db.ForeignKey("riders.id", ondelete="CASCADE"), nullable=False, index=True)

    document_type = db.Column(
        db.Enum(RiderDocumentType, name="rider_document_type", native_enum=False, length=30),
        nullable=False,
    )
    reference = db.Column(db.String(500), nullable=False)
    expiry_date = db.Column(db.Date, nullable=True)

    verification_status = db.Column(
        db.Enum(RiderDocumentVerificationStatus, name="rider_document_verification_status",
                native_enum=False, length=20),
        nullable=False,
        default=RiderDocumentVerificationStatus.PENDING,
        index=True,
    )
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    review_notes = db.Column(db.String(500), nullable=True)

    reviewer = db.relationship("User")

    __table_args__ = (
        db.Index("ix_rider_documents_rider_status", "rider_id", "verification_status"),
    )

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "document_type": self.document_type.value
            if isinstance(self.document_type, RiderDocumentType) else self.document_type,
            "reference": self.reference,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "verification_status": self.verification_status.value
            if isinstance(self.verification_status, RiderDocumentVerificationStatus) else self.verification_status,
            "reviewed_by": self.reviewer.public_id if self.reviewer else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "review_notes": self.review_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<RiderDocument {self.public_id} rider_id={self.rider_id} {self.document_type}>"
