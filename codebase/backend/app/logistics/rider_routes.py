from flask import Blueprint, request

from app.auth.decorators import require_role, current_user
from app.common.responses import success
from app.extensions import limiter
from app.logistics import rider_service, dispatch_service, delivery_service
from app.logistics.helpers import get_or_create_rider
from app.logistics.schemas import (
    RiderProfileUpdateSchema,
    RiderDocumentCreateSchema,
    AvailabilityUpdateSchema,
    LocationUpdateSchema,
    RiderZoneJoinSchema,
    OfferResponseSchema,
)

rider_bp = Blueprint("rider", __name__, url_prefix="/api/v1/rider")


@rider_bp.route("/me", methods=["GET"])
@require_role("RIDER")
def get_me():
    rider = get_or_create_rider(current_user())
    return success({"rider": rider.to_public_dict()})


@rider_bp.route("/profile", methods=["PATCH"])
@require_role("RIDER")
def update_profile():
    data = RiderProfileUpdateSchema().load(request.get_json(silent=True) or {})
    rider = get_or_create_rider(current_user())
    rider_service.upsert_vehicle(rider, data["vehicle_type"], data.get("registration_reference"))
    return success({"rider": rider.to_public_dict()}, message="Profile updated.")


@rider_bp.route("/documents", methods=["GET"])
@require_role("RIDER")
def list_documents():
    rider = get_or_create_rider(current_user())
    documents = rider_service.list_documents(rider)
    return success({"documents": [d.to_public_dict() for d in documents]})


@rider_bp.route("/documents", methods=["POST"])
@require_role("RIDER")
def create_document():
    data = RiderDocumentCreateSchema().load(request.get_json(silent=True) or {})
    rider = get_or_create_rider(current_user())
    document = rider_service.add_document(rider, data["document_type"], data["reference"], data.get("expiry_date"))
    return success({"document": document.to_public_dict()}, message="Document submitted.", status_code=201)


@rider_bp.route("/availability", methods=["GET"])
@require_role("RIDER")
def get_availability():
    rider = get_or_create_rider(current_user())
    history = rider_service.get_availability_history(rider)
    return success({
        "operational_status": rider.operational_status.value,
        "history": [h.to_public_dict() for h in history],
    })


@rider_bp.route("/availability", methods=["PATCH"])
@require_role("RIDER")
def update_availability():
    data = AvailabilityUpdateSchema().load(request.get_json(silent=True) or {})
    rider = get_or_create_rider(current_user())
    rider = rider_service.set_availability(rider, data["status"], data.get("reason"))
    return success({"rider": rider.to_public_dict()}, message="Availability updated.")


@rider_bp.route("/location", methods=["POST"])
@require_role("RIDER")
@limiter.limit("20 per minute")
def post_location():
    data = LocationUpdateSchema().load(request.get_json(silent=True) or {})
    rider = get_or_create_rider(current_user())
    rider_service.record_location(rider, data["latitude"], data["longitude"], data.get("accuracy_meters"))
    return success({"location": rider_service.get_current_location(rider)}, message="Location updated.")


@rider_bp.route("/location", methods=["GET"])
@require_role("RIDER")
def get_location():
    rider = get_or_create_rider(current_user())
    return success({"location": rider_service.get_current_location(rider)})


@rider_bp.route("/zones", methods=["GET"])
@require_role("RIDER")
def list_zones():
    rider = get_or_create_rider(current_user())
    zones = rider_service.list_rider_zones(rider)
    return success({"zones": [z.to_public_dict() for z in zones]})


@rider_bp.route("/zones", methods=["POST"])
@require_role("RIDER")
def join_zone():
    data = RiderZoneJoinSchema().load(request.get_json(silent=True) or {})
    rider = get_or_create_rider(current_user())
    zone = rider_service.join_zone(rider, data["zone_id"])
    return success({"zone": zone.to_public_dict()}, message="Zone added.", status_code=201)


@rider_bp.route("/zones/<zone_id>", methods=["DELETE"])
@require_role("RIDER")
def leave_zone(zone_id):
    rider = get_or_create_rider(current_user())
    rider_service.leave_zone(rider, zone_id)
    return success(message="Zone removed.")


@rider_bp.route("/delivery-offers", methods=["GET"])
@require_role("RIDER")
def list_offers():
    rider = get_or_create_rider(current_user())
    offers = dispatch_service.list_offers_for_rider(rider)
    return success({"offers": [o.to_public_dict() for o in offers]})


@rider_bp.route("/delivery-offers/<assignment_id>/accept", methods=["POST"])
@require_role("RIDER")
def accept_offer(assignment_id):
    rider = get_or_create_rider(current_user())
    delivery = dispatch_service.accept_offer(rider, assignment_id)
    return success({"delivery": delivery.to_public_dict()}, message="Delivery accepted.")


@rider_bp.route("/delivery-offers/<assignment_id>/reject", methods=["POST"])
@require_role("RIDER")
def reject_offer(assignment_id):
    data = OfferResponseSchema().load(request.get_json(silent=True) or {})
    rider = get_or_create_rider(current_user())
    dispatch_service.reject_offer(rider, assignment_id, data.get("reason"))
    return success(message="Offer declined.")


@rider_bp.route("/deliveries/current", methods=["GET"])
@require_role("RIDER")
def current_delivery():
    rider = get_or_create_rider(current_user())
    delivery = delivery_service.get_current_delivery_for_rider(rider)
    return success({"delivery": delivery.to_public_dict() if delivery else None})
