from flask import Blueprint, request

from app.auth.decorators import require_role, require_auth, current_user
from app.common.responses import success
from app.logistics import delivery_service, tracking_service
from app.logistics.helpers import get_or_create_rider
from app.logistics.schemas import DeliveryActionSchema

deliveries_bp = Blueprint("deliveries", __name__, url_prefix="/api/v1/deliveries")


@deliveries_bp.route("/<delivery_id>/pickup", methods=["POST"])
@require_role("RIDER")
def pickup(delivery_id):
    data = DeliveryActionSchema().load(request.get_json(silent=True) or {})
    rider = get_or_create_rider(current_user())
    delivery = delivery_service.mark_picked_up(rider, delivery_id, data.get("reason"))
    return success({"delivery": delivery.to_public_dict()}, message="Order picked up.")


@deliveries_bp.route("/<delivery_id>/start", methods=["POST"])
@require_role("RIDER")
def start(delivery_id):
    data = DeliveryActionSchema().load(request.get_json(silent=True) or {})
    rider = get_or_create_rider(current_user())
    delivery = delivery_service.start_delivering(rider, delivery_id, data.get("reason"))
    return success({"delivery": delivery.to_public_dict()}, message="Delivery in progress.")


@deliveries_bp.route("/<delivery_id>/complete", methods=["POST"])
@require_role("RIDER")
def complete(delivery_id):
    data = DeliveryActionSchema().load(request.get_json(silent=True) or {})
    rider = get_or_create_rider(current_user())
    delivery = delivery_service.complete_delivery(rider, delivery_id, data.get("reason"))
    return success({"delivery": delivery.to_public_dict()}, message="Delivery completed.")


@deliveries_bp.route("/<delivery_id>/tracking", methods=["GET"])
@require_auth
def tracking(delivery_id):
    tracking_data = tracking_service.get_tracking(current_user(), delivery_id)
    return success(tracking_data)


@deliveries_bp.route("/<delivery_id>/status-history", methods=["GET"])
@require_auth
def status_history(delivery_id):
    # Reuses the same role-scoped ownership check as tracking - a status
    # history is just as sensitive as a live location.
    tracking_data = tracking_service.get_tracking(current_user(), delivery_id)
    delivery = tracking_data["delivery"]
    from app.logistics.helpers import get_any_delivery_or_404

    full_delivery = get_any_delivery_or_404(delivery["id"])
    history = delivery_service.get_delivery_status_history(full_delivery)
    return success({"status_history": [h.to_public_dict() for h in history]})
