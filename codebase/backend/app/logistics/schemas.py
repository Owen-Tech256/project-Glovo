from marshmallow import Schema, fields, validate

from app.models.rider import RiderOnboardingStatus, RiderOperationalStatus
from app.models.rider_document import RiderDocumentType, RiderDocumentVerificationStatus
from app.models.rider_vehicle import RiderVehicleType


class RiderProfileUpdateSchema(Schema):
    """PATCH /rider/profile - the rider's operational profile, which in
    this phase is its vehicle information (vehicle_type/registration).
    Upserts the 1:1 RiderVehicle row."""

    class Meta:
        unknown = "exclude"

    vehicle_type = fields.String(required=True, validate=validate.OneOf([v.value for v in RiderVehicleType]))
    registration_reference = fields.String(required=False, allow_none=True, validate=validate.Length(max=100))


class RiderDocumentCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    document_type = fields.String(required=True, validate=validate.OneOf([d.value for d in RiderDocumentType]))
    reference = fields.String(required=True, validate=validate.Length(min=1, max=500))
    expiry_date = fields.Date(required=False, allow_none=True)


class AvailabilityUpdateSchema(Schema):
    class Meta:
        unknown = "exclude"

    # BUSY is deliberately not offered here - it is system-set only, the
    # instant a rider accepts an offer (SRS 7/8).
    status = fields.String(
        required=True,
        validate=validate.OneOf([RiderOperationalStatus.OFFLINE.value, RiderOperationalStatus.AVAILABLE.value]),
    )
    reason = fields.String(required=False, allow_none=True, validate=validate.Length(max=255))


class LocationUpdateSchema(Schema):
    class Meta:
        unknown = "exclude"

    latitude = fields.Float(required=True, validate=validate.Range(min=-90, max=90))
    longitude = fields.Float(required=True, validate=validate.Range(min=-180, max=180))
    accuracy_meters = fields.Float(required=False, allow_none=True, validate=validate.Range(min=0))


class RiderZoneJoinSchema(Schema):
    class Meta:
        unknown = "exclude"

    zone_id = fields.String(required=True)


class OfferResponseSchema(Schema):
    class Meta:
        unknown = "exclude"

    reason = fields.String(required=False, allow_none=True, validate=validate.Length(max=255))


class DeliveryActionSchema(Schema):
    class Meta:
        unknown = "exclude"

    reason = fields.String(required=False, allow_none=True, validate=validate.Length(max=500))


class AdminRiderStatusUpdateSchema(Schema):
    class Meta:
        unknown = "exclude"

    status = fields.String(required=True, validate=validate.OneOf([s.value for s in RiderOnboardingStatus]))
    reason = fields.String(required=False, allow_none=True, validate=validate.Length(max=500))


class AdminDocumentReviewSchema(Schema):
    class Meta:
        unknown = "exclude"

    verification_status = fields.String(
        required=True,
        validate=validate.OneOf(
            [RiderDocumentVerificationStatus.VERIFIED.value, RiderDocumentVerificationStatus.REJECTED.value]
        ),
    )
    review_notes = fields.String(required=False, allow_none=True, validate=validate.Length(max=500))


class AdminReassignSchema(Schema):
    class Meta:
        unknown = "exclude"

    reason = fields.String(required=False, allow_none=True, validate=validate.Length(max=500))
