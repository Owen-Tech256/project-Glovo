from flask import Blueprint, request

from app.extensions import db
from app.common.responses import success
from app.common.errors import NotFoundError
from app.auth.decorators import require_role, current_user
from app.models.user import UserRole
from app.models.customer_address import CustomerAddress
from app.addresses.schemas import AddressCreateSchema, AddressUpdateSchema

addresses_bp = Blueprint("addresses", __name__, url_prefix="/api/v1/addresses")

address_create_schema = AddressCreateSchema()
address_update_schema = AddressUpdateSchema()


def _get_owned_address_or_404(user, public_id) -> CustomerAddress:
    address = CustomerAddress.query.filter_by(public_id=public_id, user_id=user.id).first()
    if address is None:
        raise NotFoundError("Address not found.")
    return address


def _clear_other_defaults(user_id: int, except_address_id: int | None = None):
    query = CustomerAddress.query.filter_by(user_id=user_id, is_default=True)
    if except_address_id is not None:
        query = query.filter(CustomerAddress.id != except_address_id)
    query.update({"is_default": False})


@addresses_bp.get("")
@require_role(UserRole.CUSTOMER.value)
def list_my_addresses():
    user = current_user()
    addresses = (
        CustomerAddress.query.filter_by(user_id=user.id)
        .order_by(CustomerAddress.is_default.desc(), CustomerAddress.created_at.desc())
        .all()
    )
    return success({"addresses": [a.to_public_dict() for a in addresses]})


@addresses_bp.post("")
@require_role(UserRole.CUSTOMER.value)
def create_my_address():
    user = current_user()
    data = address_create_schema.load(request.get_json(silent=True) or {})

    # First address is always the default, regardless of what was sent.
    has_existing = CustomerAddress.query.filter_by(user_id=user.id).first() is not None
    is_default = data.get("is_default", False) or not has_existing

    address = CustomerAddress(user_id=user.id, **{**data, "is_default": is_default})
    db.session.add(address)
    db.session.flush()
    if is_default:
        _clear_other_defaults(user.id, except_address_id=address.id)
    db.session.commit()
    return success({"address": address.to_public_dict()}, message="Address saved.", status_code=201)


@addresses_bp.get("/<public_id>")
@require_role(UserRole.CUSTOMER.value)
def get_my_address(public_id):
    address = _get_owned_address_or_404(current_user(), public_id)
    return success({"address": address.to_public_dict()})


@addresses_bp.patch("/<public_id>")
@require_role(UserRole.CUSTOMER.value)
def update_my_address(public_id):
    user = current_user()
    address = _get_owned_address_or_404(user, public_id)
    data = address_update_schema.load(request.get_json(silent=True) or {})
    for field in (
        "label", "recipient_name", "phone", "address_line1", "address_line2",
        "city", "state", "postal_code", "country", "latitude", "longitude",
        "delivery_instructions",
    ):
        if field in data:
            setattr(address, field, data[field])

    if data.get("is_default") is True:
        address.is_default = True
        _clear_other_defaults(user.id, except_address_id=address.id)
    elif data.get("is_default") is False and address.is_default:
        # A customer may not unset their only default without designating a
        # new one - it would leave zero default addresses.
        remaining = CustomerAddress.query.filter(
            CustomerAddress.user_id == user.id, CustomerAddress.id != address.id
        ).count()
        if remaining == 0:
            address.is_default = True
        else:
            address.is_default = False

    db.session.commit()
    return success({"address": address.to_public_dict()}, message="Address updated.")


@addresses_bp.delete("/<public_id>")
@require_role(UserRole.CUSTOMER.value)
def delete_my_address(public_id):
    user = current_user()
    address = _get_owned_address_or_404(user, public_id)
    was_default = address.is_default
    db.session.delete(address)
    db.session.flush()

    if was_default:
        # Promote the most recently added remaining address to default so a
        # customer with saved addresses always has exactly one default.
        next_address = (
            CustomerAddress.query.filter_by(user_id=user.id)
            .order_by(CustomerAddress.created_at.desc())
            .first()
        )
        if next_address is not None:
            next_address.is_default = True

    db.session.commit()
    return success(message="Address deleted.")
