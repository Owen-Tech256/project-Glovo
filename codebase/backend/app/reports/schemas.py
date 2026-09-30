from marshmallow import Schema, fields, validate

from app.models.report_definition import ReportType


class ReportDefinitionCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    name = fields.String(required=True, validate=validate.Length(min=1, max=150))
    report_type = fields.String(required=True, validate=validate.OneOf([t.value for t in ReportType]))
    configuration = fields.Dict(required=False, load_default=dict)
    access_level = fields.String(required=False, load_default="analytics.view")


class ReportExportCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    report_type = fields.String(required=False, validate=validate.OneOf([t.value for t in ReportType]))
    report_definition_id = fields.String(required=False, allow_none=True)
    date_from = fields.String(required=False, allow_none=True)
    date_to = fields.String(required=False, allow_none=True)
    filters = fields.Dict(required=False, load_default=dict)
