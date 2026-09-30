import re

from marshmallow import Schema, fields, validate, validates, ValidationError

from app.models.branch import BranchStatus
from app.models.delivery_zone import DeliveryZoneStatus

_PHONE_RE = re.compile(r"^\+?[0-9]{7,15}$")


def _validate_phone(value):
    if value and not _PHONE_RE.match(value):
        raise ValidationError("Phone number format is invalid.")


class VendorUpdateSchema(Schema):
    class Meta:
        unknown = "exclude"

    name = fields.String(required=False, validate=validate.Length(min=2, max=150))
    description = fields.String(required=False, allow_none=True, validate=validate.Length(max=4000))
    phone = fields.String(required=False, allow_none=True, validate=validate.Length(max=32))
    email = fields.Email(required=False, allow_none=True)
    logo_url = fields.String(required=False, allow_none=True, validate=validate.Length(max=500))

    @validates("phone")
    def validate_phone(self, value, **kwargs):
        _validate_phone(value)


class BranchCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    name = fields.String(required=True, validate=validate.Length(min=2, max=150))
    address = fields.String(required=True, validate=validate.Length(min=3, max=500))
    latitude = fields.Float(required=True, validate=validate.Range(min=-90, max=90))
    longitude = fields.Float(required=True, validate=validate.Range(min=-180, max=180))
    phone = fields.String(required=False, allow_none=True, validate=validate.Length(max=32))

    @validates("phone")
    def validate_phone(self, value, **kwargs):
        _validate_phone(value)


class BranchUpdateSchema(Schema):
    class Meta:
        unknown = "exclude"

    name = fields.String(required=False, validate=validate.Length(min=2, max=150))
    address = fields.String(required=False, validate=validate.Length(min=3, max=500))
    latitude = fields.Float(required=False, validate=validate.Range(min=-90, max=90))
    longitude = fields.Float(required=False, validate=validate.Range(min=-180, max=180))
    phone = fields.String(required=False, allow_none=True, validate=validate.Length(max=32))
    status = fields.String(required=False, validate=validate.OneOf([s.value for s in BranchStatus]))

    @validates("phone")
    def validate_phone(self, value, **kwargs):
        _validate_phone(value)


class DeliveryZoneCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    name = fields.String(required=True, validate=validate.Length(min=2, max=150))
    center_latitude = fields.Float(required=True, validate=validate.Range(min=-90, max=90))
    center_longitude = fields.Float(required=True, validate=validate.Range(min=-180, max=180))
    radius_meters = fields.Integer(required=True, validate=validate.Range(min=1, max=100_000))


class DeliveryZoneUpdateSchema(Schema):
    class Meta:
        unknown = "exclude"

    name = fields.String(required=False, validate=validate.Length(min=2, max=150))
    center_latitude = fields.Float(required=False, validate=validate.Range(min=-90, max=90))
    center_longitude = fields.Float(required=False, validate=validate.Range(min=-180, max=180))
    radius_meters = fields.Integer(required=False, validate=validate.Range(min=1, max=100_000))
    status = fields.String(required=False, validate=validate.OneOf([s.value for s in DeliveryZoneStatus]))
