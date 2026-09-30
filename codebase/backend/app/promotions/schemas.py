from decimal import Decimal

from marshmallow import Schema, fields, validate, validates_schema, ValidationError

from app.models.promotion import PromotionType, PromotionScopeType, PromotionStatus, PromotionRuleType


class PromotionRuleSchema(Schema):
    class Meta:
        unknown = "exclude"

    rule_type = fields.String(required=True, validate=validate.OneOf([r.value for r in PromotionRuleType]))
    rule_value = fields.String(required=False, allow_none=True, validate=validate.Length(max=100))


class PromotionCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    name = fields.String(required=True, validate=validate.Length(min=1, max=150))
    description = fields.String(required=False, allow_none=True, validate=validate.Length(max=2000))
    code = fields.String(required=False, allow_none=True, validate=validate.Length(min=3, max=40))
    type = fields.String(required=True, validate=validate.OneOf([t.value for t in PromotionType]))
    value = fields.Decimal(required=True, as_string=True, places=2, validate=validate.Range(min=Decimal("0")))
    max_discount_amount = fields.Decimal(required=False, allow_none=True, as_string=True, places=2, validate=validate.Range(min=Decimal("0")))
    min_subtotal = fields.Decimal(required=False, allow_none=True, as_string=True, places=2, validate=validate.Range(min=Decimal("0")))
    scope_type = fields.String(required=False, load_default=PromotionScopeType.ORDER.value, validate=validate.OneOf([s.value for s in PromotionScopeType]))
    scope_target_ids = fields.List(fields.String(), required=False, allow_none=True)
    usage_limit_total = fields.Integer(required=False, allow_none=True, validate=validate.Range(min=1))
    usage_limit_per_customer = fields.Integer(required=False, allow_none=True, validate=validate.Range(min=1))
    status = fields.String(required=False, validate=validate.OneOf([s.value for s in PromotionStatus]))
    starts_at = fields.DateTime(required=False, allow_none=True)
    ends_at = fields.DateTime(required=False, allow_none=True)
    rules = fields.List(fields.Nested(PromotionRuleSchema), required=False, allow_none=True)

    @validates_schema
    def _validate(self, data, **kwargs):
        if data["type"] == PromotionType.PERCENTAGE.value and data["value"] > 100:
            raise ValidationError("A percentage discount cannot exceed 100.", field_name="value")
        starts_at, ends_at = data.get("starts_at"), data.get("ends_at")
        if starts_at and ends_at and starts_at >= ends_at:
            raise ValidationError("ends_at must be after starts_at.", field_name="ends_at")
        if data.get("scope_type") not in (None, PromotionScopeType.ORDER.value, PromotionScopeType.VENDOR.value) and not data.get("scope_target_ids"):
            raise ValidationError("scope_target_ids is required for this scope_type.", field_name="scope_target_ids")


class PromotionUpdateSchema(Schema):
    class Meta:
        unknown = "exclude"

    name = fields.String(required=False, validate=validate.Length(min=1, max=150))
    description = fields.String(required=False, allow_none=True, validate=validate.Length(max=2000))
    code = fields.String(required=False, allow_none=True, validate=validate.Length(min=3, max=40))
    value = fields.Decimal(required=False, as_string=True, places=2, validate=validate.Range(min=Decimal("0")))
    max_discount_amount = fields.Decimal(required=False, allow_none=True, as_string=True, places=2, validate=validate.Range(min=Decimal("0")))
    min_subtotal = fields.Decimal(required=False, allow_none=True, as_string=True, places=2, validate=validate.Range(min=Decimal("0")))
    scope_target_ids = fields.List(fields.String(), required=False, allow_none=True)
    usage_limit_total = fields.Integer(required=False, allow_none=True, validate=validate.Range(min=1))
    usage_limit_per_customer = fields.Integer(required=False, allow_none=True, validate=validate.Range(min=1))
    status = fields.String(required=False, validate=validate.OneOf([s.value for s in PromotionStatus]))
    starts_at = fields.DateTime(required=False, allow_none=True)
    ends_at = fields.DateTime(required=False, allow_none=True)
    rules = fields.List(fields.Nested(PromotionRuleSchema), required=False, allow_none=True)


class PromotionApplySchema(Schema):
    class Meta:
        unknown = "exclude"

    code = fields.String(required=True, validate=validate.Length(min=1, max=40))
