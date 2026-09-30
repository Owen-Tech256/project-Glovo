"""
The rider-facing delivery workflow once an offer has been accepted: pickup,
start-delivering, complete. Dispatch/offer concerns live in
dispatch_service.py; this module only ever advances a delivery the acting
rider already owns.
"""
from app.extensions import db
from app.models.delivery import Delivery, DeliveryStatus
from app.models.order import OrderStatus
from app.models.rider import RiderOperationalStatus
from app.logistics import state_machine as delivery_state_machine
from app.logistics import rider_service
from app.logistics.helpers import get_owned_delivery_or_404_for_rider, utcnow
from app.orders import state_machine as order_state_machine


def get_current_delivery_for_rider(rider) -> Delivery | None:
    return (
        Delivery.query.filter(
            Delivery.rider_id == rider.id,
            Delivery.status.in_([DeliveryStatus.ASSIGNED, DeliveryStatus.PICKED_UP, DeliveryStatus.DELIVERING]),
        )
        .order_by(Delivery.assigned_at.desc())
        .first()
    )


def mark_picked_up(rider, delivery_public_id: str, reason: str | None) -> Delivery:
    delivery = get_owned_delivery_or_404_for_rider(rider, delivery_public_id)
    now = utcnow()
    delivery_state_machine.apply_rider_transition(delivery, DeliveryStatus.PICKED_UP, rider.user, reason)
    delivery.picked_up_at = now
    order_state_machine.apply_rider_transition(delivery.order, OrderStatus.PICKED_UP, rider.user, reason)
    db.session.commit()
    return delivery


def start_delivering(rider, delivery_public_id: str, reason: str | None) -> Delivery:
    delivery = get_owned_delivery_or_404_for_rider(rider, delivery_public_id)
    delivery_state_machine.apply_rider_transition(delivery, DeliveryStatus.DELIVERING, rider.user, reason)
    order_state_machine.apply_rider_transition(delivery.order, OrderStatus.DELIVERING, rider.user, reason)
    db.session.commit()
    return delivery


def complete_delivery(rider, delivery_public_id: str, reason: str | None) -> Delivery:
    delivery = get_owned_delivery_or_404_for_rider(rider, delivery_public_id)
    now = utcnow()
    delivery_state_machine.apply_rider_transition(delivery, DeliveryStatus.DELIVERED, rider.user, reason)
    delivery.delivered_at = now
    order_state_machine.apply_rider_transition(delivery.order, OrderStatus.DELIVERED, rider.user, reason)

    # SRS 7: "Return rider to AVAILABLE after completion when still online."
    # A rider can never manually go OFFLINE while BUSY (see
    # rider_service.set_availability), so reaching this point always means
    # they are still online in some form.
    rider_service._record_availability_change(rider, RiderOperationalStatus.AVAILABLE, "Delivery completed.")

    db.session.commit()

    # Settlement/earning recognition happens only now, after the order is
    # truly DELIVERED (SRS 14's "configured business trigger"), in its own
    # commit - the same "separate, hook off the just-committed transition"
    # pattern Phase 4 used for dispatch (see logistics/service.py). A
    # failure here must never roll back the delivery-completion transition
    # above; settlement is independently idempotent and safe to retry.
    from app.payments import settlement_service
    settlement_service.settle_order(delivery.order)

    from app.notifications.events import notify
    from app.models.notification import NotificationCategory

    order = delivery.order
    notify(
        order.customer, NotificationCategory.DELIVERY, template_key="delivery_completed_customer",
        context={"order_number": order.public_order_number}, entity_type="ORDER", entity_id=order.public_id,
    )
    notify(
        order.branch.vendor.owner, NotificationCategory.DELIVERY, template_key="delivery_completed_vendor",
        context={"order_number": order.public_order_number}, entity_type="ORDER", entity_id=order.public_id,
    )
    notify(
        order.customer, NotificationCategory.REVIEW, template_key="review_reminder",
        context={"order_number": order.public_order_number}, entity_type="ORDER", entity_id=order.public_id,
    )

    return delivery


def get_delivery_status_history(delivery: Delivery):
    return delivery.status_history.all()
