import re

from marshmallow import Schema, fields, validate, validates, ValidationError

_PHONE_RE = re.compile(r"^\+?[0-9]{7,15}$")


def _validate_phone(value):
    if value and not _PHONE_RE.match(value):
        raise ValidationError("Phone number format is invalid.")


class AddressCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    label = fields.String(required=True, validate=validate.Length(min=1, max=100))
    recipient_name = fields.String(required=True, validate=validate.Length(min=1, max=150))
    phone = fields.String(required=True, validate=validate.Length(min=7, max=32))
    address_line1 = fields.String(required=True, validate=validate.Length(min=1, max=255))
    address_line2 = fields.String(required=False, allow_none=True, validate=validate.Length(max=255))
    city = fields.String(required=True, validate=validate.Length(min=1, max=100))
    state = fields.String(required=False, allow_none=True, validate=validate.Length(max=100))
    postal_code = fields.String(required=False, allow_none=True, validate=validate.Length(max=20))
    country = fields.String(required=True, validate=validate.Length(min=1, max=100))
    latitude = fields.Float(required=True, validate=validate.Range(min=-90, max=90))
    longitude = fields.Float(required=True, validate=validate.Range(min=-180, max=180))
    delivery_instructions = fields.String(required=False, allow_none=True, validate=validate.Length(max=2000))
    is_default = fields.Boolean(required=False, load_default=False)

    @validates("phone")
    def validate_phone(self, value, **kwargs):
        _validate_phone(value)


class AddressUpdateSchema(Schema):
    class Meta:
        unknown = "exclude"

    label = fields.String(required=False, validate=validate.Length(min=1, max=100))
    recipient_name = fields.String(required=False, validate=validate.Length(min=1, max=150))
    phone = fields.String(required=False, validate=validate.Length(min=7, max=32))
    address_line1 = fields.String(required=False, validate=validate.Length(min=1, max=255))
    address_line2 = fields.String(required=False, allow_none=True, validate=validate.Length(max=255))
    city = fields.String(required=False, validate=validate.Length(min=1, max=100))
    state = fields.String(required=False, allow_none=True, validate=validate.Length(max=100))
    postal_code = fields.String(required=False, allow_none=True, validate=validate.Length(max=20))
    country = fields.String(required=False, validate=validate.Length(min=1, max=100))
    latitude = fields.Float(required=False, validate=validate.Range(min=-90, max=90))
    longitude = fields.Float(required=False, validate=validate.Range(min=-180, max=180))
    delivery_instructions = fields.String(required=False, allow_none=True, validate=validate.Length(max=2000))
    is_default = fields.Boolean(required=False)

    @validates("phone")
    def validate_phone(self, value, **kwargs):
        _validate_phone(value)
