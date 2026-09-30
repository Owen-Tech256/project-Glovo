"""
Ownership-resolution helpers shared by the vendor-facing routes. Centralizing
these means every nested resource (branch -> zone, vendor -> category, etc.)
resolves ownership the same way, so a VENDOR can never reach another
vendor's data by guessing a public_id in the URL.
"""
from app.extensions import db
from app.models.vendor import Vendor
from app.models.branch import Branch
from app.models.delivery_zone import DeliveryZone
from app.models.category import Category
from app.models.product import Product
from app.common.errors import NotFoundError


def get_or_create_vendor(user) -> Vendor:
    """Every VENDOR-role user gets exactly one Vendor profile, provisioned
    lazily on first access so there is no separate "create my vendor
    profile" step blocking the rest of onboarding."""
    vendor = Vendor.query.filter_by(user_id=user.id).first()
    if vendor is None:
        vendor = Vendor(user_id=user.id, name=user.full_name)
        db.session.add(vendor)
        db.session.commit()
    return vendor


def get_owned_branch_or_404(vendor: Vendor, branch_public_id: str) -> Branch:
    branch = Branch.query.filter_by(public_id=branch_public_id, vendor_id=vendor.id).first()
    if branch is None:
        raise NotFoundError("Branch not found.")
    return branch


def get_owned_zone_or_404(branch: Branch, zone_public_id: str) -> DeliveryZone:
    zone = DeliveryZone.query.filter_by(public_id=zone_public_id, branch_id=branch.id).first()
    if zone is None:
        raise NotFoundError("Delivery zone not found.")
    return zone


def get_owned_category_or_404(vendor: Vendor, category_public_id: str) -> Category:
    category = Category.query.filter_by(public_id=category_public_id, vendor_id=vendor.id).first()
    if category is None:
        raise NotFoundError("Category not found.")
    return category


def get_owned_product_or_404(vendor: Vendor, product_public_id: str) -> Product:
    product = (
        Product.query.join(Category)
        .filter(Product.public_id == product_public_id, Category.vendor_id == vendor.id)
        .first()
    )
    if product is None:
        raise NotFoundError("Product not found.")
    return product
