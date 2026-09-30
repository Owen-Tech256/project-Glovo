import enum

from app.extensions import db
from app.models.base import PublicIdMixin, TimestampMixin


class RiderVehicleType(str, enum.Enum):
    BICYCLE = "BICYCLE"
    SCOOTER = "SCOOTER"
    MOTORCYCLE = "MOTORCYCLE"
    CAR = "CAR"
    ON_FOOT = "ON_FOOT"


class RiderVehicleStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class RiderVehicle(db.Model, PublicIdMixin, TimestampMixin):
    """One vehicle profile per rider (SRS ER: RIDER 1:1 RIDER_VEHICLE).
    `registration_reference` is optional since ON_FOOT/BICYCLE riders in
    many jurisdictions have nothing to register."""

    __tablename__ = "rider_vehicles"

    id = db.Column(db.Integer, primary_key=True)
    rider_id = db.Column(
        db.Integer, db.ForeignKey("riders.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    vehicle_type = db.Column(
        db.Enum(RiderVehicleType, name="rider_vehicle_type", native_enum=False, length=20),
        nullable=False,
    )
    registration_reference = db.Column(db.String(100), nullable=True)
    status = db.Column(
        db.Enum(RiderVehicleStatus, name="rider_vehicle_status", native_enum=False, length=20),
        nullable=False,
        default=RiderVehicleStatus.ACTIVE,
    )

    def to_public_dict(self) -> dict:
        return {
            "id": self.public_id,
            "vehicle_type": self.vehicle_type.value
            if isinstance(self.vehicle_type, RiderVehicleType) else self.vehicle_type,
            "registration_reference": self.registration_reference,
            "status": self.status.value if isinstance(self.status, RiderVehicleStatus) else self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):  # pragma: no cover
        return f"<RiderVehicle {self.public_id} rider_id={self.rider_id} {self.vehicle_type}>"
