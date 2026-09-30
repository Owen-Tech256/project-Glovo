from decimal import Decimal

from marshmallow import Schema, fields, validate

from app.models.product import ProductStatus
from app.models.branch_product import BranchProductAvailability


class CategoryCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    name = fields.String(required=True, validate=validate.Length(min=1, max=150))
    description = fields.String(required=False, allow_none=True, validate=validate.Length(max=2000))
    image_url = fields.String(required=False, allow_none=True, validate=validate.Length(max=500))
    sort_order = fields.Integer(required=False, load_default=0)
    is_active = fields.Boolean(required=False, load_default=True)


class CategoryUpdateSchema(Schema):
    class Meta:
        unknown = "exclude"

    name = fields.String(required=False, validate=validate.Length(min=1, max=150))
    description = fields.String(required=False, allow_none=True, validate=validate.Length(max=2000))
    image_url = fields.String(required=False, allow_none=True, validate=validate.Length(max=500))
    sort_order = fields.Integer(required=False)
    is_active = fields.Boolean(required=False)


class ProductCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    category_id = fields.String(required=True)
    name = fields.String(required=True, validate=validate.Length(min=1, max=200))
    description = fields.String(required=False, allow_none=True, validate=validate.Length(max=4000))
    sku = fields.String(required=False, allow_none=True, validate=validate.Length(max=64))
    price = fields.Decimal(required=True, as_string=True, places=2, validate=validate.Range(min=Decimal("0")))


class ProductUpdateSchema(Schema):
    class Meta:
        unknown = "exclude"

    category_id = fields.String(required=False)
    name = fields.String(required=False, validate=validate.Length(min=1, max=200))
    description = fields.String(required=False, allow_none=True, validate=validate.Length(max=4000))
    sku = fields.String(required=False, allow_none=True, validate=validate.Length(max=64))
    price = fields.Decimal(required=False, as_string=True, places=2, validate=validate.Range(min=Decimal("0")))
    status = fields.String(required=False, validate=validate.OneOf([s.value for s in ProductStatus]))


class ProductImageCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    image_url = fields.String(required=True, validate=validate.Length(min=1, max=500))
    alt_text = fields.String(required=False, allow_none=True, validate=validate.Length(max=255))
    sort_order = fields.Integer(required=False, load_default=0)


class ProductImageUpdateSchema(Schema):
    class Meta:
        unknown = "exclude"

    image_url = fields.String(required=False, validate=validate.Length(min=1, max=500))
    alt_text = fields.String(required=False, allow_none=True, validate=validate.Length(max=255))
    sort_order = fields.Integer(required=False)


class BranchProductUpsertSchema(Schema):
    """Sets availability/pricing for a product at a branch. `product_id` is
    read from the URL, not the body, so this only carries the mutable
    fields."""

    class Meta:
        unknown = "exclude"

    price_override = fields.Decimal(required=False, allow_none=True, as_string=True, places=2, validate=validate.Range(min=Decimal("0")))
    availability_status = fields.String(
        required=False, validate=validate.OneOf([s.value for s in BranchProductAvailability])
    )


class DiscoveryQuerySchema(Schema):
    class Meta:
        unknown = "exclude"

    lat = fields.Float(required=True, validate=validate.Range(min=-90, max=90))
    lng = fields.Float(required=True, validate=validate.Range(min=-180, max=180))
    search = fields.String(required=False, allow_none=True, validate=validate.Length(max=150))
    min_rating = fields.Float(required=False, allow_none=True, validate=validate.Range(min=0, max=5))
    sort = fields.String(required=False, load_default="distance", validate=validate.OneOf(["distance", "rating", "name"]))
    page = fields.Integer(required=False, load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(required=False, load_default=20, validate=validate.Range(min=1, max=100))
