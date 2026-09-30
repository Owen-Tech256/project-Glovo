from marshmallow import Schema, fields, validate

from app.models.support_ticket import TicketCategory, TicketPriority, TicketStatus, RelatedEntityType, MessageVisibility


class TicketCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    category = fields.String(required=True, validate=validate.OneOf([c.value for c in TicketCategory]))
    priority = fields.String(required=False, validate=validate.OneOf([p.value for p in TicketPriority]))
    subject = fields.String(required=True, validate=validate.Length(min=1, max=200))
    message = fields.String(required=True, validate=validate.Length(min=1, max=5000))
    related_entity_type = fields.String(required=False, allow_none=True, validate=validate.OneOf([t.value for t in RelatedEntityType]))
    related_entity_id = fields.String(required=False, allow_none=True)


class MessageCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    body = fields.String(required=True, validate=validate.Length(min=1, max=5000))


class StaffMessageCreateSchema(MessageCreateSchema):
    visibility = fields.String(required=False, validate=validate.OneOf([v.value for v in MessageVisibility]), load_default="PUBLIC")


class AttachmentCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    filename = fields.String(required=True, validate=validate.Length(min=1, max=255))
    reference = fields.String(required=True, validate=validate.Length(min=1, max=500))
    content_type = fields.String(required=False, allow_none=True, validate=validate.Length(max=100))
    message_id = fields.String(required=False, allow_none=True)


class AssignTicketSchema(Schema):
    class Meta:
        unknown = "exclude"

    agent_id = fields.String(required=False, allow_none=True)


class TicketStatusUpdateSchema(Schema):
    class Meta:
        unknown = "exclude"

    status = fields.String(required=True, validate=validate.OneOf([s.value for s in TicketStatus]))
    resolution_summary = fields.String(required=False, allow_none=True, validate=validate.Length(max=4000))
