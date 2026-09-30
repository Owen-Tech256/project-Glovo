from marshmallow import Schema, fields, validate

from app.models.notification import NotificationCategory


class NotificationPreferenceUpdateSchema(Schema):
    class Meta:
        unknown = "exclude"

    category = fields.String(required=True, validate=validate.OneOf([c.value for c in NotificationCategory]))
    channel = fields.String(required=True, validate=validate.OneOf(["EMAIL", "SMS", "PUSH"]))
    enabled = fields.Boolean(required=True)
