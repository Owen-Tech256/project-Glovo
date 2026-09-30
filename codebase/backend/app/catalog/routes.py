from flask import Blueprint, request

from app.extensions import db
from app.common.responses import success
from app.common.errors import NotFoundError
from app.auth.decorators import require_role, current_user
from app.models.user import UserRole
from app.models.vendor import Vendor, VendorStatus
from app.models.branch import Branch, BranchStatus
from app.models.category import Category
from app.models.product import Product, ProductStatus
from app.models.product_image import ProductImage
from app.models.branch_product import BranchProduct, BranchProductAvailability
from app.vendors.helpers import (
    get_or_create_vendor,
    get_owned_branch_or_404,
    get_owned_category_or_404,
    get_owned_product_or_404,
)
from app.catalog.schemas import (
    CategoryCreateSchema,
    CategoryUpdateSchema,
    ProductCreateSchema,
    ProductUpdateSchema,
    ProductImageCreateSchema,
    ProductImageUpdateSchema,
    BranchProductUpsertSchema,
    DiscoveryQuerySchema,
)
from app.catalog.discovery import find_branches_serving

catalog_bp = Blueprint("catalog", __name__, url_prefix="/api/v1")

category_create_schema = CategoryCreateSchema()
category_update_schema = CategoryUpdateSchema()
product_create_schema = ProductCreateSchema()
product_update_schema = ProductUpdateSchema()
image_create_schema = ProductImageCreateSchema()
image_update_schema = ProductImageUpdateSchema()
branch_product_schema = BranchProductUpsertSchema()
discovery_query_schema = DiscoveryQuerySchema()


# --- Categories (vendor self-service) ---------------------------------------

@catalog_bp.get("/vendors/me/categories")
@require_role(UserRole.VENDOR.value)
def list_my_categories():
    vendor = get_or_create_vendor(current_user())
    categories = vendor.categories.order_by(Category.sort_order, Category.created_at.desc()).all()
    return success({"categories": [c.to_public_dict() for c in categories]})


@catalog_bp.post("/vendors/me/categories")
@require_role(UserRole.VENDOR.value)
def create_my_category():
    vendor = get_or_create_vendor(current_user())
    data = category_create_schema.load(request.get_json(silent=True) or {})
    category = Category(vendor_id=vendor.id, **data)
    db.session.add(category)
    db.session.commit()
    return success({"category": category.to_public_dict()}, message="Category created.", status_code=201)


@catalog_bp.get("/vendors/me/categories/<public_id>")
@require_role(UserRole.VENDOR.value)
def get_my_category(public_id):
    vendor = get_or_create_vendor(current_user())
    category = get_owned_category_or_404(vendor, public_id)
    return success({"category": category.to_public_dict()})


@catalog_bp.patch("/vendors/me/categories/<public_id>")
@require_role(UserRole.VENDOR.value)
def update_my_category(public_id):
    vendor = get_or_create_vendor(current_user())
    category = get_owned_category_or_404(vendor, public_id)
    data = category_update_schema.load(request.get_json(silent=True) or {})
    for field in ("name", "description", "image_url", "sort_order", "is_active"):
        if field in data:
            setattr(category, field, data[field])
    db.session.commit()
    return success({"category": category.to_public_dict()}, message="Category updated.")


@catalog_bp.delete("/vendors/me/categories/<public_id>")
@require_role(UserRole.VENDOR.value)
def delete_my_category(public_id):
    """Archives (deactivates) rather than deletes - products already
    assigned to this category are catalog records that may later be
    referenced by orders."""
    vendor = get_or_create_vendor(current_user())
    category = get_owned_category_or_404(vendor, public_id)
    category.is_active = False
    db.session.commit()
    return success(message="Category deactivated.")


# --- Products (vendor self-service) -----------------------------------------

@catalog_bp.get("/vendors/me/products")
@require_role(UserRole.VENDOR.value)
def list_my_products():
    vendor = get_or_create_vendor(current_user())
    products = (
        Product.query.join(Category)
        .filter(Category.vendor_id == vendor.id)
        .order_by(Product.created_at.desc())
        .all()
    )
    return success({"products": [p.to_public_dict() for p in products]})


@catalog_bp.post("/vendors/me/products")
@require_role(UserRole.VENDOR.value)
def create_my_product():
    vendor = get_or_create_vendor(current_user())
    data = product_create_schema.load(request.get_json(silent=True) or {})
    category = get_owned_category_or_404(vendor, data.pop("category_id"))
    product = Product(category_id=category.id, **data)
    db.session.add(product)
    db.session.commit()
    return success({"product": product.to_public_dict()}, message="Product created.", status_code=201)


@catalog_bp.get("/vendors/me/products/<public_id>")
@require_role(UserRole.VENDOR.value)
def get_my_product(public_id):
    vendor = get_or_create_vendor(current_user())
    product = get_owned_product_or_404(vendor, public_id)
    return success({"product": product.to_public_dict()})


@catalog_bp.patch("/vendors/me/products/<public_id>")
@require_role(UserRole.VENDOR.value)
def update_my_product(public_id):
    vendor = get_or_create_vendor(current_user())
    product = get_owned_product_or_404(vendor, public_id)
    data = product_update_schema.load(request.get_json(silent=True) or {})
    if "category_id" in data:
        category = get_owned_category_or_404(vendor, data.pop("category_id"))
        product.category_id = category.id
    for field in ("name", "description", "sku", "price", "status"):
        if field in data:
            setattr(product, field, data[field])
    db.session.commit()
    return success({"product": product.to_public_dict()}, message="Product updated.")


@catalog_bp.delete("/vendors/me/products/<public_id>")
@require_role(UserRole.VENDOR.value)
def delete_my_product(public_id):
    """Archives rather than deletes - see Category delete for rationale."""
    vendor = get_or_create_vendor(current_user())
    product = get_owned_product_or_404(vendor, public_id)
    product.status = ProductStatus.ARCHIVED
    db.session.commit()
    return success(message="Product archived.")


# --- Product images (vendor self-service) -----------------------------------

@catalog_bp.post("/vendors/me/products/<product_public_id>/images")
@require_role(UserRole.VENDOR.value)
def add_my_product_image(product_public_id):
    vendor = get_or_create_vendor(current_user())
    product = get_owned_product_or_404(vendor, product_public_id)
    data = image_create_schema.load(request.get_json(silent=True) or {})
    image = ProductImage(product_id=product.id, **data)
    db.session.add(image)
    db.session.commit()
    return success({"image": image.to_public_dict()}, message="Image added.", status_code=201)


@catalog_bp.patch("/vendors/me/products/<product_public_id>/images/<image_public_id>")
@require_role(UserRole.VENDOR.value)
def update_my_product_image(product_public_id, image_public_id):
    vendor = get_or_create_vendor(current_user())
    product = get_owned_product_or_404(vendor, product_public_id)
    image = ProductImage.query.filter_by(public_id=image_public_id, product_id=product.id).first()
    if image is None:
        raise NotFoundError("Product image not found.")
    data = image_update_schema.load(request.get_json(silent=True) or {})
    for field in ("image_url", "alt_text", "sort_order"):
        if field in data:
            setattr(image, field, data[field])
    db.session.commit()
    return success({"image": image.to_public_dict()}, message="Image updated.")


@catalog_bp.delete("/vendors/me/products/<product_public_id>/images/<image_public_id>")
@require_role(UserRole.VENDOR.value)
def delete_my_product_image(product_public_id, image_public_id):
    vendor = get_or_create_vendor(current_user())
    product = get_owned_product_or_404(vendor, product_public_id)
    image = ProductImage.query.filter_by(public_id=image_public_id, product_id=product.id).first()
    if image is None:
        raise NotFoundError("Product image not found.")
    db.session.delete(image)
    db.session.commit()
    return success(message="Image removed.")


# --- Branch-product availability & pricing (vendor self-service) -----------

@catalog_bp.get("/vendors/me/branches/<branch_public_id>/products")
@require_role(UserRole.VENDOR.value)
def list_my_branch_products(branch_public_id):
    vendor = get_or_create_vendor(current_user())
    branch = get_owned_branch_or_404(vendor, branch_public_id)
    links = branch.branch_products.order_by(BranchProduct.created_at.desc()).all()
    return success({"branch_products": [bp.to_public_dict() for bp in links]})


@catalog_bp.put("/vendors/me/branches/<branch_public_id>/products/<product_public_id>")
@require_role(UserRole.VENDOR.value)
def set_my_branch_product(branch_public_id, product_public_id):
    """Idempotent upsert: creates or updates the availability/price-override
    row linking this product to this branch. (branch_id, product_id) is
    enforced unique at the database level."""
    vendor = get_or_create_vendor(current_user())
    branch = get_owned_branch_or_404(vendor, branch_public_id)
    product = get_owned_product_or_404(vendor, product_public_id)
    data = branch_product_schema.load(request.get_json(silent=True) or {})

    link = BranchProduct.query.filter_by(branch_id=branch.id, product_id=product.id).first()
    if link is None:
        link = BranchProduct(branch_id=branch.id, product_id=product.id)
        db.session.add(link)
    if "price_override" in data:
        link.price_override = data["price_override"]
    if "availability_status" in data:
        link.availability_status = data["availability_status"]
    db.session.commit()
    return success({"branch_product": link.to_public_dict()}, message="Branch availability updated.")


@catalog_bp.delete("/vendors/me/branches/<branch_public_id>/products/<product_public_id>")
@require_role(UserRole.VENDOR.value)
def remove_my_branch_product(branch_public_id, product_public_id):
    vendor = get_or_create_vendor(current_user())
    branch = get_owned_branch_or_404(vendor, branch_public_id)
    product = get_owned_product_or_404(vendor, product_public_id)
    link = BranchProduct.query.filter_by(branch_id=branch.id, product_id=product.id).first()
    if link is None:
        raise NotFoundError("This product is not linked to this branch.")
    db.session.delete(link)
    db.session.commit()
    return success(message="Product removed from branch.")


# --- Public catalog browsing (customer discovery) ---------------------------

@catalog_bp.get("/vendors/<vendor_public_id>/categories")
def list_public_categories(vendor_public_id):
    vendor = Vendor.query.filter_by(public_id=vendor_public_id).first()
    if vendor is None or vendor.status != VendorStatus.ACTIVE:
        raise NotFoundError("Vendor not found.")
    categories = vendor.categories.filter_by(is_active=True).order_by(Category.sort_order).all()
    return success({"categories": [c.to_public_dict() for c in categories]})


@catalog_bp.get("/categories/<category_public_id>/products")
def list_public_category_products(category_public_id):
    category = Category.query.filter_by(public_id=category_public_id, is_active=True).first()
    if category is None or category.vendor.status != VendorStatus.ACTIVE:
        raise NotFoundError("Category not found.")
    products = category.products.filter_by(status=ProductStatus.ACTIVE).order_by(Product.name).all()
    return success({"products": [p.to_public_dict() for p in products]})


@catalog_bp.get("/products/<product_public_id>")
def get_public_product(product_public_id):
    product = Product.query.filter_by(public_id=product_public_id, status=ProductStatus.ACTIVE).first()
    if product is None or not product.category.is_active or product.category.vendor.status != VendorStatus.ACTIVE:
        raise NotFoundError("Product not found.")
    return success({"product": product.to_public_dict()})


@catalog_bp.get("/branches/<branch_public_id>/products")
def list_public_branch_products(branch_public_id):
    """A branch's live, orderable-in-a-later-phase catalog: only products
    marked AVAILABLE at this specific branch, that are themselves ACTIVE."""
    branch = Branch.query.filter_by(public_id=branch_public_id, status=BranchStatus.ACTIVE).first()
    if branch is None or branch.vendor.status != VendorStatus.ACTIVE:
        raise NotFoundError("Branch not found.")
    links = (
        branch.branch_products.join(Product)
        .filter(
            BranchProduct.availability_status == BranchProductAvailability.AVAILABLE,
            Product.status == ProductStatus.ACTIVE,
        )
        .all()
    )
    return success({"branch_products": [bp.to_public_dict() for bp in links]})


# --- Location-aware discovery -----------------------------------------------

@catalog_bp.get("/discovery/branches")
def discover_branches():
    args = discovery_query_schema.load(request.args.to_dict())
    ranked = find_branches_serving(
        latitude=args["lat"],
        longitude=args["lng"],
        search=args.get("search"),
        min_rating=args.get("min_rating"),
        sort=args["sort"],
    )

    total = len(ranked)
    per_page = args["per_page"]
    page = args["page"]
    total_pages = max(1, -(-total // per_page))  # ceil division without importing math
    start = (page - 1) * per_page
    page_items = ranked[start : start + per_page]

    return success({
        "branches": [branch.to_public_dict(distance_meters=distance) for branch, distance in page_items],
        "pagination": {"page": page, "per_page": per_page, "total": total, "total_pages": total_pages},
    })
