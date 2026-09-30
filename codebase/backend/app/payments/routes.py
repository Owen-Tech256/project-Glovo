from flask import Blueprint, request

from app.auth.decorators import require_role, current_user
from app.common.responses import success
from app.payments import payment_service, refund_service
from app.payments.schemas import PaymentCreateSchema, RefundRequestSchema

payments_bp = Blueprint("payments", __name__, url_prefix="/api/v1")


def _pagination_dict(pagination):
    return {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "total_pages": pagination.pages,
    }


# --- Payments (customer) ----------------------------------------------

@payments_bp.route("/payments", methods=["POST"])
@require_role("CUSTOMER")
def create_payment():
    data = PaymentCreateSchema().load(request.get_json(silent=True) or {})
    customer = current_user()
    payment, was_created = payment_service.create_payment(
        customer, data["order_id"], data["method"], data.get("provider"), data.get("idempotency_key")
    )
    message = "Payment submitted." if was_created else "Payment already submitted for this request."
    return success({"payment": payment.to_public_dict()}, message=message, status_code=201 if was_created else 200)


@payments_bp.route("/payments/<payment_public_id>", methods=["GET"])
@require_role("CUSTOMER")
def get_payment(payment_public_id):
    customer = current_user()
    payment = payment_service.get_owned_payment_or_404(customer, payment_public_id)
    return success({"payment": payment.to_public_dict()})


@payments_bp.route("/payments/<payment_public_id>/verify", methods=["POST"])
@require_role("CUSTOMER")
def verify_payment(payment_public_id):
    customer = current_user()
    payment = payment_service.verify_payment(customer, payment_public_id)
    return success({"payment": payment.to_public_dict()}, message="Payment verified.")


@payments_bp.route("/orders/<order_public_id>/payments", methods=["GET"])
@require_role("CUSTOMER")
def list_order_payments(order_public_id):
    customer = current_user()
    payments = payment_service.list_payments_for_order(customer, order_public_id)
    return success({"payments": [p.to_public_dict() for p in payments]})


# --- Webhooks (public, signature-verified - no user auth) ---------------

@payments_bp.route("/webhooks/payments/<provider>", methods=["POST"])
def payment_webhook(provider):
    raw_body = request.get_data()
    signature_header = request.headers.get("X-Signature")
    result = payment_service.process_webhook_event(provider, raw_body, signature_header)
    # Always 200 for a recognized/processed/already-processed event, so
    # the provider does not retry-storm a call we have already handled
    # (SRS 6: duplicate delivery must be harmless).
    return success(result, message="Webhook processed.")


# --- Refunds (customer-initiated, order-scoped) --------------------------

@payments_bp.route("/orders/<order_public_id>/refund-request", methods=["POST"])
@require_role("CUSTOMER")
def request_refund(order_public_id):
    data = RefundRequestSchema().load(request.get_json(silent=True) or {})
    customer = current_user()
    refund, was_created = refund_service.request_refund(
        customer, order_public_id, data.get("amount"), data["reason"], data.get("idempotency_key")
    )
    message = "Refund requested." if was_created else "Refund already requested for this request."
    return success({"refund": refund.to_public_dict()}, message=message, status_code=201 if was_created else 200)


@payments_bp.route("/orders/<order_public_id>/refunds", methods=["GET"])
@require_role("CUSTOMER")
def list_order_refunds(order_public_id):
    customer = current_user()
    refunds = refund_service.list_refunds_for_order(customer, order_public_id)
    return success({"refunds": [r.to_public_dict() for r in refunds]})
