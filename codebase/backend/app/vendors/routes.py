from flask import Blueprint, request

from app.extensions import db
from app.common.responses import success
from app.auth.decorators import require_role, current_user
from app.models.user import UserRole
from app.models.vendor import Vendor, VendorStatus
from app.models.branch import Branch, BranchStatus
from app.models.delivery_zone import DeliveryZone
from app.common.errors import NotFoundError
from app.vendors.helpers import get_or_create_vendor, get_owned_branch_or_404, get_owned_zone_or_404
from app.vendors.schemas import (
    VendorUpdateSchema,
    BranchCreateSchema,
    BranchUpdateSchema,
    DeliveryZoneCreateSchema,
    DeliveryZoneUpdateSchema,
)

vendors_bp = Blueprint("vendors", __name__, url_prefix="/api/v1/vendors")

vendor_update_schema = VendorUpdateSchema()
branch_create_schema = BranchCreateSchema()
branch_update_schema = BranchUpdateSchema()
zone_create_schema = DeliveryZoneCreateSchema()
zone_update_schema = DeliveryZoneUpdateSchema()


# --- Vendor profile (self-service) -----------------------------------------

@vendors_bp.get("/me")
@require_role(UserRole.VENDOR.value)
def get_my_vendor():
    vendor = get_or_create_vendor(current_user())
    return success({"vendor": vendor.to_public_dict()})


@vendors_bp.patch("/me")
@require_role(UserRole.VENDOR.value)
def update_my_vendor():
    vendor = get_or_create_vendor(current_user())
    data = vendor_update_schema.load(request.get_json(silent=True) or {})
    for field in ("name", "description", "phone", "email", "logo_url"):
        if field in data:
            setattr(vendor, field, data[field])
    db.session.commit()
    return success({"vendor": vendor.to_public_dict()}, message="Vendor profile updated.")


# --- Public vendor / branch browsing (customer discovery) ------------------

@vendors_bp.get("/<public_id>")
def get_public_vendor(public_id):
    vendor = Vendor.query.filter_by(public_id=public_id).first()
    if vendor is None or vendor.status != VendorStatus.ACTIVE:
        raise NotFoundError("Vendor not found.")
    return success({"vendor": vendor.to_public_dict()})


@vendors_bp.get("/<public_id>/branches")
def list_public_vendor_branches(public_id):
    vendor = Vendor.query.filter_by(public_id=public_id).first()
    if vendor is None or vendor.status != VendorStatus.ACTIVE:
        raise NotFoundError("Vendor not found.")
    branches = vendor.branches.filter_by(status=BranchStatus.ACTIVE).order_by(Branch.name).all()
    return success({"branches": [b.to_public_dict() for b in branches]})


# --- Branches (self-service) ------------------------------------------------

@vendors_bp.get("/me/branches")
@require_role(UserRole.VENDOR.value)
def list_my_branches():
    vendor = get_or_create_vendor(current_user())
    branches = vendor.branches.order_by(Branch.created_at.desc()).all()
    return success({"branches": [b.to_public_dict() for b in branches]})


@vendors_bp.post("/me/branches")
@require_role(UserRole.VENDOR.value)
def create_my_branch():
    vendor = get_or_create_vendor(current_user())
    data = branch_create_schema.load(request.get_json(silent=True) or {})
    branch = Branch(vendor_id=vendor.id, **data)
    db.session.add(branch)
    db.session.commit()
    return success({"branch": branch.to_public_dict()}, message="Branch created.", status_code=201)


@vendors_bp.get("/me/branches/<public_id>")
@require_role(UserRole.VENDOR.value)
def get_my_branch(public_id):
    vendor = get_or_create_vendor(current_user())
    branch = get_owned_branch_or_404(vendor, public_id)
    return success({"branch": branch.to_public_dict()})


@vendors_bp.patch("/me/branches/<public_id>")
@require_role(UserRole.VENDOR.value)
def update_my_branch(public_id):
    vendor = get_or_create_vendor(current_user())
    branch = get_owned_branch_or_404(vendor, public_id)
    data = branch_update_schema.load(request.get_json(silent=True) or {})
    for field in ("name", "address", "latitude", "longitude", "phone", "status"):
        if field in data:
            setattr(branch, field, data[field])
    db.session.commit()
    return success({"branch": branch.to_public_dict()}, message="Branch updated.")


@vendors_bp.delete("/me/branches/<public_id>")
@require_role(UserRole.VENDOR.value)
def delete_my_branch(public_id):
    """Branches may already be referenced by zones/branch-products and could
    be referenced by orders in a later phase, so this closes the branch
    (soft) rather than deleting the row."""
    vendor = get_or_create_vendor(current_user())
    branch = get_owned_branch_or_404(vendor, public_id)
    branch.status = BranchStatus.CLOSED
    db.session.commit()
    return success(message="Branch closed.")


# --- Delivery zones (self-service, nested under branch) --------------------

@vendors_bp.get("/me/branches/<branch_public_id>/zones")
@require_role(UserRole.VENDOR.value)
def list_my_zones(branch_public_id):
    vendor = get_or_create_vendor(current_user())
    branch = get_owned_branch_or_404(vendor, branch_public_id)
    zones = branch.delivery_zones.order_by(DeliveryZone.created_at.desc()).all()
    return success({"delivery_zones": [z.to_public_dict() for z in zones]})


@vendors_bp.post("/me/branches/<branch_public_id>/zones")
@require_role(UserRole.VENDOR.value)
def create_my_zone(branch_public_id):
    vendor = get_or_create_vendor(current_user())
    branch = get_owned_branch_or_404(vendor, branch_public_id)
    data = zone_create_schema.load(request.get_json(silent=True) or {})
    zone = DeliveryZone(branch_id=branch.id, **data)
    db.session.add(zone)
    db.session.commit()
    return success({"delivery_zone": zone.to_public_dict()}, message="Delivery zone created.", status_code=201)


@vendors_bp.patch("/me/branches/<branch_public_id>/zones/<zone_public_id>")
@require_role(UserRole.VENDOR.value)
def update_my_zone(branch_public_id, zone_public_id):
    vendor = get_or_create_vendor(current_user())
    branch = get_owned_branch_or_404(vendor, branch_public_id)
    zone = get_owned_zone_or_404(branch, zone_public_id)
    data = zone_update_schema.load(request.get_json(silent=True) or {})
    for field in ("name", "center_latitude", "center_longitude", "radius_meters", "status"):
        if field in data:
            setattr(zone, field, data[field])
    db.session.commit()
    return success({"delivery_zone": zone.to_public_dict()}, message="Delivery zone updated.")


@vendors_bp.delete("/me/branches/<branch_public_id>/zones/<zone_public_id>")
@require_role(UserRole.VENDOR.value)
def delete_my_zone(branch_public_id, zone_public_id):
    vendor = get_or_create_vendor(current_user())
    branch = get_owned_branch_or_404(vendor, branch_public_id)
    zone = get_owned_zone_or_404(branch, zone_public_id)
    db.session.delete(zone)
    db.session.commit()
    return success(message="Delivery zone deleted.")
