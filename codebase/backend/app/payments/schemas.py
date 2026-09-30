from decimal import Decimal

from marshmallow import Schema, fields, validate, validates_schema, ValidationError

from app.models.commission_rule import CommissionScopeType


class PaymentCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    order_id = fields.String(required=True, validate=validate.Length(min=1, max=64))
    method = fields.String(required=False, load_default="CARD", validate=validate.Length(min=1, max=32))
    provider = fields.String(required=False, allow_none=True, validate=validate.Length(max=32))
    idempotency_key = fields.String(required=False, allow_none=True, validate=validate.Length(max=128))


class WebhookEventSchema(Schema):
    """Documents the mock provider's webhook payload shape for reference
    only - the webhook route reads the raw body itself (signature
    verification needs the exact bytes), it does not run this schema."""

    class Meta:
        unknown = "exclude"

    event_id = fields.String(required=True)
    event_type = fields.String(required=True)
    provider_reference = fields.String(required=False, allow_none=True)
    failure_reason = fields.String(required=False, allow_none=True)


class RefundRequestSchema(Schema):
    class Meta:
        unknown = "exclude"

    amount = fields.Decimal(required=False, allow_none=True, places=2, validate=validate.Range(min=Decimal("0.01")))
    reason = fields.String(required=True, validate=validate.Length(min=1, max=500))
    idempotency_key = fields.String(required=False, allow_none=True, validate=validate.Length(max=128))


class RefundRejectSchema(Schema):
    class Meta:
        unknown = "exclude"

    reason = fields.String(required=False, allow_none=True, validate=validate.Length(max=500))


class PayoutRequestSchema(Schema):
    class Meta:
        unknown = "exclude"

    amount = fields.Decimal(required=False, allow_none=True, places=2, validate=validate.Range(min=Decimal("0.01")))
    destination_reference = fields.String(required=True, validate=validate.Length(min=1, max=255))
    idempotency_key = fields.String(required=False, allow_none=True, validate=validate.Length(max=128))


class WalletAdjustmentSchema(Schema):
    class Meta:
        unknown = "exclude"

    rider_id = fields.String(required=True, validate=validate.Length(min=1, max=64))
    amount = fields.Decimal(required=True, places=2)
    reason = fields.String(required=True, validate=validate.Length(min=1, max=500))

    @validates_schema
    def check_amount_nonzero(self, data, **kwargs):
        if data.get("amount") == 0:
            raise ValidationError("Adjustment amount cannot be zero.", field_name="amount")


class CommissionRuleCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    name = fields.String(required=True, validate=validate.Length(min=1, max=150))
    percentage_rate = fields.Decimal(required=False, load_default=Decimal("0"), places=4,
                                      validate=validate.Range(min=Decimal("0"), max=Decimal("1")))
    fixed_amount = fields.Decimal(required=False, load_default=Decimal("0"), places=2,
                                   validate=validate.Range(min=Decimal("0")))
    scope_type = fields.String(required=False, load_default=CommissionScopeType.GLOBAL.value,
                                validate=validate.OneOf([s.value for s in CommissionScopeType]))
    scope_id = fields.Integer(required=False, allow_none=True)
    effective_from = fields.DateTime(required=False, allow_none=True)
    effective_to = fields.DateTime(required=False, allow_none=True)


class CommissionRuleUpdateSchema(Schema):
    class Meta:
        unknown = "exclude"

    name = fields.String(required=False, validate=validate.Length(min=1, max=150))
    percentage_rate = fields.Decimal(required=False, places=4, validate=validate.Range(min=Decimal("0"), max=Decimal("1")))
    fixed_amount = fields.Decimal(required=False, places=2, validate=validate.Range(min=Decimal("0")))
    status = fields.String(required=False, validate=validate.OneOf(["ACTIVE", "INACTIVE"]))
    effective_to = fields.DateTime(required=False, allow_none=True)
