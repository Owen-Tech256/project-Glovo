from marshmallow import Schema, fields, validate

from app.models.dispute import DisputeCategory, DisputeStatus, DisputePriority
from app.models.dispute_action import DisputeActionType, FINANCIAL_ACTION_TYPES

_NON_FINANCIAL_ACTION_TYPES = [t.value for t in DisputeActionType if t not in FINANCIAL_ACTION_TYPES]


class DisputeCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    order_id = fields.String(required=True)
    category = fields.String(required=True, validate=validate.OneOf([c.value for c in DisputeCategory]))
    description = fields.String(required=True, validate=validate.Length(min=1, max=4000))
    delivery_id = fields.String(required=False, allow_none=True)
    payment_id = fields.String(required=False, allow_none=True)
    refund_id = fields.String(required=False, allow_none=True)
    ticket_id = fields.String(required=False, allow_none=True)


class EvidenceCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    evidence_type = fields.String(required=True, validate=validate.OneOf(["PHOTO", "DOCUMENT", "STATEMENT", "OTHER"]))
    secure_reference = fields.String(required=False, allow_none=True, validate=validate.Length(max=500))
    description = fields.String(required=False, allow_none=True, validate=validate.Length(max=2000))


class DisputeStatusUpdateSchema(Schema):
    class Meta:
        unknown = "exclude"

    status = fields.String(required=True, validate=validate.OneOf([s.value for s in DisputeStatus]))
    resolution = fields.String(required=False, allow_none=True, validate=validate.Length(max=4000))


class DisputePrioritySchema(Schema):
    class Meta:
        unknown = "exclude"

    priority = fields.String(required=True, validate=validate.OneOf([p.value for p in DisputePriority]))


class DisputeActionCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    # REFUND_ISSUED/PARTIAL_REFUND_ISSUED are never posted through this
    # endpoint - they can only be produced by resolve_with_refund (below),
    # which is the one path that actually calls Phase 5 refund services.
    action_type = fields.String(required=True, validate=validate.OneOf(_NON_FINANCIAL_ACTION_TYPES))
    reason = fields.String(required=False, allow_none=True, validate=validate.Length(max=2000))


class DisputeRefundResolveSchema(Schema):
    class Meta:
        unknown = "exclude"

    amount = fields.Decimal(required=False, allow_none=True, places=2)
    reason = fields.String(required=True, validate=validate.Length(min=1, max=1000))
