"""
Role-scoped read access to a delivery's status and location, backing the
customer/vendor tracking views and the shared /deliveries/{id}/tracking
endpoint (SRS 9). Every lookup here is an ownership check first, a read
second - a customer, vendor, or rider can only ever reach their own data;
only ADMIN sees everything (SRS 13).
"""
from app.common.errors import NotFoundError
from app.models.delivery import Delivery, DeliveryStatus
from app.models.user import UserRole
from app.logistics.helpers import (
    is_location_fresh,
    get_or_create_rider,
    get_owned_delivery_or_404_for_rider,
    get_delivery_for_branch_or_404,
    get_any_delivery_or_404,
)

# Delivery states in which exposing the rider's live position is
# meaningful and proportionate (SRS 13: "Minimize exposed rider
# personal/location information"). Before a rider is assigned there is
# nothing to show; after DELIVERED the trip is over.
LOCATION_VISIBLE_STATUSES = {DeliveryStatus.ASSIGNED, DeliveryStatus.PICKED_UP, DeliveryStatus.DELIVERING}


def _serialize(delivery: Delivery) -> dict:
    show_location = delivery.status in LOCATION_VISIBLE_STATUSES
    latest = delivery.locations.first() if show_location else None
    rider_location = None
    if latest is not None:
        rider_location = {**latest.to_public_dict(), "is_stale": not is_location_fresh(latest.recorded_at)}

    return {
        "delivery": delivery.to_public_dict(),
        "rider_location": rider_location,
    }


def serialize_delivery_tracking(delivery: Delivery) -> dict:
    return _serialize(delivery)


def get_delivery_for_customer(customer, order_public_id: str) -> Delivery:
    from app.orders import service as order_service

    order = order_service.get_owned_order_or_404(customer, order_public_id)
    if order.delivery is None:
        raise NotFoundError("This order does not have a delivery yet.")
    return order.delivery


def get_delivery_for_vendor_by_order(vendor, order_public_id: str) -> Delivery:
    from app.models.branch import Branch
    from app.models.order import Order

    order = (
        Order.query.join(Branch, Order.branch_id == Branch.id)
        .filter(Order.public_id == order_public_id, Branch.vendor_id == vendor.id)
        .first()
    )
    if order is None:
        raise NotFoundError("Order not found.")
    if order.delivery is None:
        raise NotFoundError("This order does not have a delivery yet.")
    return order.delivery


def get_delivery_for_vendor(vendor, delivery_public_id: str) -> Delivery:
    from app.logistics.helpers import get_delivery_for_branch_or_404

    return get_delivery_for_branch_or_404(vendor, delivery_public_id)


def get_tracking(current_user, delivery_public_id: str) -> dict:
    """Single shared entry point for GET /deliveries/{id}/tracking. Scoped
    by the caller's role; anyone who isn't a party to this delivery gets a
    404, never a 403, so the endpoint doesn't confirm a delivery's
    existence to someone unrelated to it."""
    from app.vendors.helpers import get_or_create_vendor

    if current_user.role == UserRole.ADMIN:
        delivery = get_any_delivery_or_404(delivery_public_id)
    elif current_user.role == UserRole.RIDER:
        rider = get_or_create_rider(current_user)
        delivery = get_owned_delivery_or_404_for_rider(rider, delivery_public_id)
    elif current_user.role == UserRole.VENDOR:
        vendor = get_or_create_vendor(current_user)
        delivery = get_delivery_for_branch_or_404(vendor, delivery_public_id)
    elif current_user.role == UserRole.CUSTOMER:
        delivery = Delivery.query.filter_by(public_id=delivery_public_id).first()
        if delivery is None or delivery.order is None or delivery.order.customer_id != current_user.id:
            raise NotFoundError("Delivery not found.")
    else:  # pragma: no cover - defensive, no other roles exist
        raise NotFoundError("Delivery not found.")

    return _serialize(delivery)
