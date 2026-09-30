import re

from marshmallow import Schema, fields, validate, validates, validates_schema, ValidationError

from app.models.user import UserRole

PASSWORD_MIN_LENGTH = 8
_PHONE_RE = re.compile(r"^\+?[0-9]{7,15}$")

# Roles that may self-register through the public API. ADMIN is deliberately
# excluded - admin accounts must be provisioned out-of-band (see
# scripts/create_admin.py), never through a public endpoint.
PUBLIC_REGISTERABLE_ROLES = {UserRole.CUSTOMER.value, UserRole.VENDOR.value, UserRole.RIDER.value}


def _validate_password_strength(value: str):
    if len(value) < PASSWORD_MIN_LENGTH:
        raise ValidationError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters long.")
    if not re.search(r"[A-Za-z]", value):
        raise ValidationError("Password must contain at least one letter.")
    if not re.search(r"[0-9]", value):
        raise ValidationError("Password must contain at least one number.")


class RegisterSchema(Schema):
    full_name = fields.String(required=True, validate=validate.Length(min=2, max=150))
    email = fields.Email(required=True)
    phone = fields.String(required=True, validate=validate.Length(min=7, max=32))
    password = fields.String(required=True, load_only=True)
    password_confirmation = fields.String(required=True, load_only=True)
    role = fields.String(
        required=False,
        load_default=UserRole.CUSTOMER.value,
        validate=validate.OneOf(sorted(PUBLIC_REGISTERABLE_ROLES)),
    )

    @validates("phone")
    def validate_phone(self, value, **kwargs):
        if not _PHONE_RE.match(value):
            raise ValidationError("Phone number format is invalid.")

    @validates("password")
    def validate_password(self, value, **kwargs):
        _validate_password_strength(value)

    @validates_schema
    def validate_passwords_match(self, data, **kwargs):
        if data.get("password") != data.get("password_confirmation"):
            raise ValidationError("Password and confirmation do not match.", field_name="password_confirmation")


class LoginSchema(Schema):
    # Accept either an email or a phone number in the same field, per the
    # "Email/phone field" login UX described in the implementation prompt.
    identifier = fields.String(required=True)
    password = fields.String(required=True, load_only=True)
    remember_me = fields.Boolean(required=False, load_default=False)


class RefreshSchema(Schema):
    refresh_token = fields.String(required=True, load_only=True)


class LogoutSchema(Schema):
    refresh_token = fields.String(required=True, load_only=True)


class ForgotPasswordSchema(Schema):
    email = fields.Email(required=True)


class ResetPasswordSchema(Schema):
    token = fields.String(required=True, load_only=True)
    password = fields.String(required=True, load_only=True)
    password_confirmation = fields.String(required=True, load_only=True)

    @validates("password")
    def validate_password(self, value, **kwargs):
        _validate_password_strength(value)

    @validates_schema
    def validate_passwords_match(self, data, **kwargs):
        if data.get("password") != data.get("password_confirmation"):
            raise ValidationError("Password and confirmation do not match.", field_name="password_confirmation")


class UpdateMeSchema(Schema):
    # Deliberately excludes email, phone, role, and status: identity and
    # permission fields are not self-service in Phase 1. Unknown/disallowed
    # keys (e.g. a client trying to slip `role` or `status` through) are
    # silently dropped rather than erroring, so this can never become a
    # privilege-escalation vector.
    class Meta:
        unknown = "exclude"

    full_name = fields.String(required=False, validate=validate.Length(min=2, max=150))
