from marshmallow import Schema, fields, validate

from app.models.admin_role import AdminRoleStatus


class RoleCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    name = fields.String(required=True, validate=validate.Length(min=2, max=50))
    description = fields.String(required=False, allow_none=True, validate=validate.Length(max=255))
    permission_keys = fields.List(fields.String(), required=False, load_default=list)


class RoleUpdateSchema(Schema):
    class Meta:
        unknown = "exclude"

    description = fields.String(required=False, allow_none=True, validate=validate.Length(max=255))
    permission_keys = fields.List(fields.String(), required=False, allow_none=True)
    status = fields.String(required=False, validate=validate.OneOf([s.value for s in AdminRoleStatus]))


class AssignStaffRoleSchema(Schema):
    class Meta:
        unknown = "exclude"

    role_id = fields.String(required=False, allow_none=True)
