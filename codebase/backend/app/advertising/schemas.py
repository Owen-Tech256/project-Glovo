from decimal import Decimal

from marshmallow import Schema, fields, validate, validates_schema, ValidationError

from app.models.ad_campaign import AdObjective, AdTargetType, AdPricingModel


class AdCampaignCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    name = fields.String(required=True, validate=validate.Length(min=1, max=150))
    objective = fields.String(required=False, load_default=AdObjective.SPONSORED_LISTING.value, validate=validate.OneOf([o.value for o in AdObjective]))
    target_type = fields.String(required=True, validate=validate.OneOf([t.value for t in AdTargetType]))
    target_id = fields.String(required=False, allow_none=True)
    pricing_model = fields.String(required=False, load_default=AdPricingModel.CPC.value, validate=validate.OneOf([p.value for p in AdPricingModel]))
    bid_amount = fields.Decimal(required=True, as_string=True, places=4, validate=validate.Range(min=Decimal("0.0001")))
    daily_budget = fields.Decimal(required=False, allow_none=True, as_string=True, places=2, validate=validate.Range(min=Decimal("0.01")))
    total_budget = fields.Decimal(required=True, as_string=True, places=2, validate=validate.Range(min=Decimal("0.01")))
    starts_at = fields.DateTime(required=False, allow_none=True)
    ends_at = fields.DateTime(required=False, allow_none=True)

    @validates_schema
    def _validate(self, data, **kwargs):
        if data["target_type"] != AdTargetType.VENDOR.value and not data.get("target_id"):
            raise ValidationError("target_id is required for this target_type.", field_name="target_id")
        starts_at, ends_at = data.get("starts_at"), data.get("ends_at")
        if starts_at and ends_at and starts_at >= ends_at:
            raise ValidationError("ends_at must be after starts_at.", field_name="ends_at")


class AdCampaignUpdateSchema(Schema):
    class Meta:
        unknown = "exclude"

    name = fields.String(required=False, validate=validate.Length(min=1, max=150))
    bid_amount = fields.Decimal(required=False, as_string=True, places=4, validate=validate.Range(min=Decimal("0.0001")))
    daily_budget = fields.Decimal(required=False, allow_none=True, as_string=True, places=2, validate=validate.Range(min=Decimal("0.01")))
    total_budget = fields.Decimal(required=False, as_string=True, places=2, validate=validate.Range(min=Decimal("0.01")))
    starts_at = fields.DateTime(required=False, allow_none=True)
    ends_at = fields.DateTime(required=False, allow_none=True)


class AdCampaignRejectSchema(Schema):
    class Meta:
        unknown = "exclude"

    reason = fields.String(required=True, validate=validate.Length(min=1, max=500))


class AdEventSchema(Schema):
    class Meta:
        unknown = "exclude"

    event_type = fields.String(required=True, validate=validate.OneOf(["IMPRESSION", "CLICK"]))
    event_reference = fields.String(required=False, allow_none=True, validate=validate.Length(max=128))
