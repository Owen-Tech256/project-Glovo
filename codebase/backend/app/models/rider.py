import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class RiderOnboardingStatus(str, enum.Enum):
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class RiderOperationalStatus(str, enum.Enum):
    OFFLINE = "OFFLINE"
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"


# Onboarding states from which a rider is still allowed to hold ONLINE
# (AVAILABLE/BUSY) operational status. Everything else (PENDING,
# UNDER_REVIEW, REJECTED, SUSPENDED) is dispatch-ineligible - see
# Rider.is_dispatch_eligible below, the single source of truth the dispatch
# engine and the availability service both defer to.
_ONBOARDING_STATES_ELIGIBLE_FOR_ONLINE = {RiderOnboardingStatus.APPROVED}


class Rider(db.Model, PublicIdMixin, TimestampMixin):
    """One operational profile per RIDER-role user (SRS 5: "Create one rider
    profile per RIDER user"). Vehicle and document details live in their own
    tables (rider_vehicles, rider_documents) since a rider can have several
    documents and (in a later phase) potentially more than one vehicle.

    `current_latitude`/`current_longitude`/`location_updated_at` are a
    deliberate denormalization of the latest row in `rider_locations` (the
    full history table). Dispatch has to filter "all approved+available
    riders" by freshness and then rank by distance on every request; reading
    that off the rider row directly avoids an N+1 "latest location per
    rider" query. `rider_locations` remains the append-only source of truth
    used for tracking history - see app/logistics/location_service.py.
    """

    __tablename__ = "riders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    onboarding_status = db.Column(
        db.Enum(RiderOnboardingStatus, name="rider_onboarding_status", native_enum=False, length=20),
        nullable=False,
        default=RiderOnboardingStatus.PENDING,
        index=True,
    )
    operational_status = db.Column(
        db.Enum(RiderOperationalStatus, name="rider_operational_status", native_enum=False, length=20),
        nullable=False,
        default=RiderOperationalStatus.OFFLINE,
        index=True,
    )
    approved_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Phase 6: cached rating aggregate over this rider's PUBLISHED reviews -
    # see the matching column on app/models/vendor.py for the recompute
    # contract.
    rating_average = db.Column(db.Numeric(3, 2), nullable=True)
    rating_count = db.Column(db.Integer, nullable=False, default=0)

    current_latitude = db.Column(db.Numeric(9, 6), nullable=True)
    current_longitude = db.Column(db.Numeric(9, 6), nullable=True)
    location_updated_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)

    user = db.relationship("User", backref=db.backref("rider_profile", uselist=False))
    documents = db.relationship(
        "RiderDocument", backref="rider", lazy="dynamic", cascade="all, delete-orphan",
        order_by="RiderDocument.created_at.desc()",
    )
    vehicle = db.relationship(
        "RiderVehicle", backref="rider", uselist=False, cascade="all, delete-orphan"
    )
    availability_history = db.relationship(
        "RiderAvailabilityHistory", backref="rider", lazy="dynamic", cascade="all, delete-orphan",
        order_by="RiderAvailabilityHistory.changed_at.desc()",
    )
    locations = db.relationship(
        "RiderLocation", backref="rider", lazy="dynamic", cascade="all, delete-orphan"
    )
    zones = db.relationship(
        "RiderZone", backref="rider", lazy="dynamic", cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.CheckConstraint(
            "current_latitude IS NULL OR (current_latitude >= -90 AND current_latitude <= 90)",
            name="ck_riders_current_latitude_range",
        ),
        db.CheckConstraint(
            "current_longitude IS NULL OR (current_longitude >= -180 AND current_longitude <= 180)",
            name="ck_riders_current_longitude_range",
        ),
        db.Index("ix_riders_onboarding_operational", "onboarding_status", "operational_status"),
    )

    @property
    def is_dispatch_eligible(self) -> bool:
        """Only APPROVED riders may ever be online/dispatch-eligible (SRS 5:
        "Only approved operational riders are dispatch-eligible")."""
        return self.onboarding_status in _ONBOARDING_STATES_ELIGIBLE_FOR_ONLINE

    def to_public_dict(self, include_vehicle: bool = True) -> dict:
        data = {
            "id": self.public_id,
            "user_id": self.user.public_id if self.user else None,
            "full_name": self.user.full_name if self.user else None,
            "onboarding_status": self.onboarding_status.value
            if isinstance(self.onboarding_status, RiderOnboardingStatus) else self.onboarding_status,
            "operational_status": self.operational_status.value
            if isinstance(self.operational_status, RiderOperationalStatus) else self.operational_status,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rating_average": str(self.rating_average) if self.rating_average is not None else None,
            "rating_count": self.rating_count,
            "location_updated_at": self.location_updated_at.isoformat() if self.location_updated_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_vehicle:
            data["vehicle"] = self.vehicle.to_public_dict() if self.vehicle else None
        return data

    def __repr__(self):  # pragma: no cover
        return f"<Rider {self.public_id} onboarding={self.onboarding_status} operational={self.operational_status}>"
