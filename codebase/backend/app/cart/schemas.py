from flask import current_app
from marshmallow import Schema, fields, validate, validates, ValidationError


def _validate_quantity_ceiling(value):
    max_quantity = current_app.config.get("CART_MAX_ITEM_QUANTITY", 20)
    if value > max_quantity:
        raise ValidationError(f"Quantity cannot exceed {max_quantity} per item.")


class AddCartItemSchema(Schema):
    class Meta:
        unknown = "exclude"

    branch_id = fields.String(required=True)
    product_id = fields.String(required=True)
    quantity = fields.Integer(required=False, load_default=1, validate=validate.Range(min=1))

    @validates("quantity")
    def validate_quantity(self, value, **kwargs):
        _validate_quantity_ceiling(value)


class UpdateCartItemSchema(Schema):
    class Meta:
        unknown = "exclude"

    quantity = fields.Integer(required=True, validate=validate.Range(min=1))

    @validates("quantity")
    def validate_quantity(self, value, **kwargs):
        _validate_quantity_ceiling(value)
