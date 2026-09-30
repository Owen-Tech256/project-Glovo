from flask import Blueprint, request

from app.extensions import db
from app.common.responses import success
from app.common.errors import NotFoundError
from app.auth.decorators import require_role
from app.models.user import UserRole
from app.models.vendor import Vendor, VendorStatus
from app.models.branch import Branch, BranchStatus
from app.models.category import Category
from marshmallow import Schema, fields, validate

admin_catalog_bp = Blueprint("admin_catalog", __name__, url_prefix="/api/v1/admin")


class _VendorStatusSchema(Schema):
    status = fields.String(required=True, validate=validate.OneOf([s.value for s in VendorStatus]))


class _BranchStatusSchema(Schema):
    status = fields.String(required=True, validate=validate.OneOf([s.value for s in BranchStatus]))


vendor_status_schema = _VendorStatusSchema()
branch_status_schema = _BranchStatusSchema()


# --- Vendor oversight --------------------------------------------------------

@admin_catalog_bp.get("/vendors")
@require_role(UserRole.ADMIN.value)
def list_vendors():
    page = request.args.get("page", default=1, type=int)
    per_page = min(request.args.get("per_page", default=20, type=int), 100)
    status_filter = request.args.get("status")

    query = Vendor.query
    if status_filter:
        query = query.filter(Vendor.status == status_filter)

    pagination = query.order_by(Vendor.created_at.desc()).paginate(
        page=max(page, 1), per_page=max(per_page, 1), error_out=False
    )
    return success(
        {
            "vendors": [v.to_public_dict(include_owner=True) for v in pagination.items],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "total_pages": pagination.pages,
            },
        }
    )


@admin_catalog_bp.get("/vendors/<public_id>")
@require_role(UserRole.ADMIN.value)
def get_vendor(public_id):
    vendor = Vendor.query.filter_by(public_id=public_id).first()
    if vendor is None:
        raise NotFoundError("Vendor not found.")
    return success(
        {
            "vendor": vendor.to_public_dict(include_owner=True),
            "branch_count": vendor.branches.count(),
            "category_count": vendor.categories.count(),
        }
    )


@admin_catalog_bp.patch("/vendors/<public_id>/status")
@require_role(UserRole.ADMIN.value)
def update_vendor_status(public_id):
    vendor = Vendor.query.filter_by(public_id=public_id).first()
    if vendor is None:
        raise NotFoundError("Vendor not found.")
    data = vendor_status_schema.load(request.get_json(silent=True) or {})
    vendor.status = data["status"]
    db.session.commit()
    return success({"vendor": vendor.to_public_dict(include_owner=True)}, message="Vendor status updated.")


@admin_catalog_bp.get("/vendors/<public_id>/branches")
@require_role(UserRole.ADMIN.value)
def list_vendor_branches(public_id):
    vendor = Vendor.query.filter_by(public_id=public_id).first()
    if vendor is None:
        raise NotFoundError("Vendor not found.")
    branches = vendor.branches.order_by(Branch.created_at.desc()).all()
    return success({"branches": [b.to_public_dict() for b in branches]})


@admin_catalog_bp.get("/vendors/<public_id>/catalog")
@require_role(UserRole.ADMIN.value)
def get_vendor_catalog(public_id):
    """Read-only catalog oversight view: every category with its products
    nested underneath."""
    vendor = Vendor.query.filter_by(public_id=public_id).first()
    if vendor is None:
        raise NotFoundError("Vendor not found.")
    categories = vendor.categories.order_by(Category.sort_order).all()
    return success(
        {
            "categories": [
                {**c.to_public_dict(), "products": [p.to_public_dict() for p in c.products]}
                for c in categories
            ]
        }
    )


# --- Branch oversight ---------------------------------------------------------

@admin_catalog_bp.patch("/branches/<public_id>/status")
@require_role(UserRole.ADMIN.value)
def update_branch_status(public_id):
    branch = Branch.query.filter_by(public_id=public_id).first()
    if branch is None:
        raise NotFoundError("Branch not found.")
    data = branch_status_schema.load(request.get_json(silent=True) or {})
    branch.status = data["status"]
    db.session.commit()
    return success({"branch": branch.to_public_dict()}, message="Branch status updated.")
