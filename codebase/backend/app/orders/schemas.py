from marshmallow import Schema, fields, validate

from app.models.order import OrderStatus


class CheckoutRequestSchema(Schema):
    """Shared shape for both checkout/validate and checkout/summary: the
    customer names which branch cart and which saved address they intend
    to check out with."""

    class Meta:
        unknown = "exclude"

    branch_id = fields.String(required=True)
    address_id = fields.String(required=True)


class CreateOrderSchema(Schema):
    class Meta:
        unknown = "exclude"

    branch_id = fields.String(required=True)
    address_id = fields.String(required=True)
    # Optional client-generated key so a retried/double-submitted request
    # (e.g. a double-tapped "Place order" button, or a network retry)
    # replays the original order instead of creating a second one.
    idempotency_key = fields.String(required=False, allow_none=True, validate=validate.Length(max=128))


class CancelOrderSchema(Schema):
    class Meta:
        unknown = "exclude"

    reason = fields.String(required=False, allow_none=True, validate=validate.Length(max=500))


class VendorTransitionSchema(Schema):
    class Meta:
        unknown = "exclude"

    to_status = fields.String(required=True, validate=validate.OneOf([s.value for s in OrderStatus]))
    reason = fields.String(required=False, allow_none=True, validate=validate.Length(max=500))
