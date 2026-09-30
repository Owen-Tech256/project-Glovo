from marshmallow import Schema, fields, validate

from app.models.review import ReviewTargetType, ReviewStatus, ReviewReportStatus


class ReviewCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    target_type = fields.String(required=True, validate=validate.OneOf([t.value for t in ReviewTargetType]))
    target_id = fields.String(required=True)
    rating = fields.Integer(required=True, validate=validate.Range(min=1, max=5))
    body = fields.String(required=False, allow_none=True, validate=validate.Length(max=2000))


class ReviewUpdateSchema(Schema):
    class Meta:
        unknown = "exclude"

    rating = fields.Integer(required=False, validate=validate.Range(min=1, max=5))
    body = fields.String(required=False, allow_none=True, validate=validate.Length(max=2000))


class ReviewReportSchema(Schema):
    class Meta:
        unknown = "exclude"

    reason = fields.String(required=True, validate=validate.Length(min=1, max=500))


class ReviewResponseSchema(Schema):
    class Meta:
        unknown = "exclude"

    body = fields.String(required=True, validate=validate.Length(min=1, max=2000))


class ReviewModerateSchema(Schema):
    class Meta:
        unknown = "exclude"

    status = fields.String(required=True, validate=validate.OneOf([s.value for s in ReviewStatus]))


class ReviewReportResolveSchema(Schema):
    class Meta:
        unknown = "exclude"

    status = fields.String(required=True, validate=validate.OneOf([ReviewReportStatus.REVIEWED.value, ReviewReportStatus.DISMISSED.value]))
    hide_review = fields.Boolean(required=False, load_default=False)
