"""
Payment creation, verification, webhook processing (SRS 6). The single
authoritative confirmation path is `confirm_payment_success` - every other
entry point (a synchronous charge response, a client-triggered /verify
call, or an inbound webhook) all funnel into it, and it is the only place
in this codebase allowed to move an order into PAYMENT_CONFIRMED
(implementation prompt 3: "Only authoritative success may confirm payment
for the order").
"""
import json

from flask import current_app

from app.extensions import db
from app.common.errors import NotFoundError, ValidationAppError, ConflictError
from app.models.order import Order, OrderStatus
from app.models.payment import Payment, PaymentStatus
from app.models.payment_transaction import PaymentTransaction, PaymentTransactionType, PaymentTransactionStatus
from app.models.payment_webhook_event import PaymentWebhookEvent, WebhookProcessingStatus
from app.models.financial_account import FinancialAccountType, FinancialAccountOwnerType
from app.models.financial_transaction import FinancialTransactionType, FinancialReferenceType
from app.models.ledger_entry import LedgerEntryType
from app.orders import state_machine as order_state_machine
from app.payments import ledger_service
from app.payments.ledger_service import LedgerLeg
from app.payments.providers import get_provider


# --- Creation --------------------------------------------------------------

def get_owned_order_for_payment_or_404(customer, order_public_id: str) -> Order:
    order = Order.query.filter_by(public_id=order_public_id, customer_id=customer.id).first()
    if order is None:
        raise NotFoundError("Order not found.")
    return order


def create_payment(customer, order_public_id: str, method: str, provider_name: str | None,
                    idempotency_key: str | None) -> tuple[Payment, bool]:
    if idempotency_key:
        existing = Payment.query.filter_by(customer_id=customer.id, idempotency_key=idempotency_key).first()
        if existing is not None:
            return existing, False

    order = get_owned_order_for_payment_or_404(customer, order_public_id)

    already_succeeded = Payment.query.filter_by(order_id=order.id, status=PaymentStatus.SUCCEEDED).first()
    if already_succeeded is not None:
        raise ConflictError("This order has already been paid.", code="ORDER_ALREADY_PAID")

    if order.status != OrderStatus.PENDING_PAYMENT:
        raise ValidationAppError(
            f"This order is not awaiting payment (current status: {order.status.value}).",
            code="ORDER_NOT_PAYABLE",
        )

    provider_name = provider_name or current_app.config.get("DEFAULT_PAYMENT_PROVIDER", "mock")

    payment = Payment(
        order_id=order.id,
        customer_id=customer.id,
        amount=order.total,  # server-calculated - never trust a client-supplied amount (SRS 5)
        currency=ledger_service.default_currency(),
        method=method,
        provider=provider_name,
        status=PaymentStatus.INITIATED,
        idempotency_key=idempotency_key,
    )
    db.session.add(payment)
    db.session.flush()

    _attempt_charge(payment)
    db.session.commit()

    from app.notifications.events import notify
    from app.models.notification import NotificationCategory

    if payment.status == PaymentStatus.FAILED:
        notify(
            order.customer, NotificationCategory.PAYMENT, template_key="payment_failed",
            context={"order_number": order.public_order_number}, entity_type="ORDER", entity_id=order.public_id,
        )
    return payment, True


def _attempt_charge(payment: Payment) -> None:
    provider = get_provider(payment.provider)
    result = provider.charge(payment)

    transaction = PaymentTransaction(
        payment_id=payment.id,
        type=PaymentTransactionType.CHARGE,
        amount=payment.amount,
        currency=payment.currency,
        status=PaymentTransactionStatus.SUCCEEDED if result.status == "SUCCEEDED" else (
            PaymentTransactionStatus.PENDING if result.status == "PENDING" else PaymentTransactionStatus.FAILED
        ),
        provider_reference=result.provider_reference,
        external_event_id=result.external_event_id,
        failure_reason=result.failure_reason,
        processed_at=ledger_service.utcnow(),
    )
    db.session.add(transaction)

    payment.provider_reference = result.provider_reference
    if result.status == "SUCCEEDED":
        payment.status = PaymentStatus.PENDING  # confirm_payment_success below will finalize + post the ledger
        db.session.flush()
        confirm_payment_success(payment)
    elif result.status == "PENDING":
        payment.status = PaymentStatus.PENDING
    else:
        payment.status = PaymentStatus.FAILED
        payment.failure_reason = result.failure_reason


# --- Authoritative confirmation (the only path that may set PAYMENT_CONFIRMED) --

def confirm_payment_success(payment: Payment) -> Payment:
    """Idempotent and safe under concurrency: row-locks the Payment first,
    so a /verify call racing an inbound webhook for the same payment can
    never both post the ledger or both transition the order (implementation
    prompt 12: "Two identical payment confirmations must result in one
    financial posting")."""
    locked = Payment.query.filter_by(id=payment.id).with_for_update().first()

    if locked.status == PaymentStatus.SUCCEEDED:
        return locked  # already posted - no-op replay

    locked.status = PaymentStatus.SUCCEEDED
    locked.succeeded_at = ledger_service.utcnow()

    _post_capture_ledger(locked)

    order = locked.order
    if order.status == OrderStatus.PENDING_PAYMENT:
        order_state_machine.apply_transition(
            order, OrderStatus.PAYMENT_CONFIRMED, actor_user=None, reason="Payment captured."
        )

    db.session.commit()

    from app.notifications.events import notify
    from app.models.notification import NotificationCategory

    notify(
        order.customer, NotificationCategory.PAYMENT, template_key="payment_succeeded",
        context={"amount": str(locked.amount), "currency": locked.currency, "order_number": order.public_order_number},
        entity_type="ORDER", entity_id=order.public_id,
    )
    notify(
        order.customer, NotificationCategory.ORDER, template_key="order_confirmed",
        context={"order_number": order.public_order_number},
        entity_type="ORDER", entity_id=order.public_id,
    )
    return locked


def _post_capture_ledger(payment: Payment) -> None:
    customer_account = ledger_service.get_or_create_account(
        FinancialAccountType.CUSTOMER_CLEARING, FinancialAccountOwnerType.CUSTOMER, owner_id=payment.customer_id
    )
    platform_account = ledger_service.get_or_create_account(
        FinancialAccountType.PLATFORM_CLEARING, FinancialAccountOwnerType.PLATFORM
    )
    legs = [
        LedgerLeg(customer_account, LedgerEntryType.DEBIT, payment.amount, description=f"Payment {payment.public_id}"),
        LedgerLeg(platform_account, LedgerEntryType.CREDIT, payment.amount, description=f"Payment {payment.public_id}"),
    ]
    ledger_service.post_transaction(
        FinancialTransactionType.PAYMENT_CAPTURE,
        FinancialReferenceType.PAYMENT,
        payment.id,
        legs,
        idempotency_key=f"payment_capture:{payment.id}",
        currency=payment.currency,
        description=f"Payment captured for order {payment.order.public_order_number}.",
    )


def mark_payment_failed(payment: Payment, reason: str) -> Payment:
    locked = Payment.query.filter_by(id=payment.id).with_for_update().first()
    if locked.status in (PaymentStatus.SUCCEEDED, PaymentStatus.FAILED, PaymentStatus.CANCELLED):
        return locked
    locked.status = PaymentStatus.FAILED
    locked.failure_reason = reason
    db.session.commit()

    from app.notifications.events import notify
    from app.models.notification import NotificationCategory

    notify(
        locked.order.customer, NotificationCategory.PAYMENT, template_key="payment_failed",
        context={"order_number": locked.order.public_order_number},
        entity_type="ORDER", entity_id=locked.order.public_id,
    )
    return locked


# --- Verification (SRS 6: server-side verification) -------------------------

def verify_payment(customer, payment_public_id: str) -> Payment:
    payment = get_owned_payment_or_404(customer, payment_public_id)
    if payment.status == PaymentStatus.SUCCEEDED:
        return payment

    provider = get_provider(payment.provider)
    result = provider.verify(payment)

    db.session.add(
        PaymentTransaction(
            payment_id=payment.id,
            type=PaymentTransactionType.VERIFY,
            amount=payment.amount,
            currency=payment.currency,
            status=PaymentTransactionStatus.SUCCEEDED if result.status == "SUCCEEDED" else (
                PaymentTransactionStatus.PENDING if result.status == "PENDING" else PaymentTransactionStatus.FAILED
            ),
            provider_reference=result.provider_reference,
            failure_reason=result.failure_reason,
            processed_at=ledger_service.utcnow(),
        )
    )
    db.session.commit()

    if result.status == "SUCCEEDED":
        return confirm_payment_success(payment)
    if result.status == "FAILED":
        return mark_payment_failed(payment, result.failure_reason or "Payment verification failed.")
    return payment


# --- Webhook processing (SRS 6: dedupe + signature verification) -----------

def process_webhook_event(provider_name: str, raw_body: bytes, signature_header: str | None) -> dict:
    provider = get_provider(provider_name)
    signature_ok = provider.verify_webhook_signature(raw_body, signature_header)

    try:
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except (ValueError, UnicodeDecodeError):
        payload = {}

    external_event_id = str(payload.get("event_id") or "")
    if not signature_ok or not external_event_id:
        db.session.add(
            PaymentWebhookEvent(
                provider=provider_name,
                external_event_id=external_event_id or f"invalid:{ledger_service.utcnow().timestamp()}",
                event_type=payload.get("event_type"),
                signature_verified=signature_ok,
                payload_reference=json.dumps(payload)[:2000],
                processing_status=WebhookProcessingStatus.REJECTED,
                processed_at=ledger_service.utcnow(),
            )
        )
        db.session.commit()
        raise ValidationAppError("Invalid webhook signature or payload.", code="INVALID_WEBHOOK")

    # Dedup: a second delivery of an already-seen event is recognized here
    # and never reprocessed (SRS 6: "Deduplicate webhook events").
    existing = PaymentWebhookEvent.query.filter_by(provider=provider_name, external_event_id=external_event_id).first()
    if existing is not None:
        return {"status": "ALREADY_PROCESSED", "event": existing.to_public_dict()}

    event_type = payload.get("event_type")
    provider_reference = payload.get("provider_reference")
    payment = None
    if provider_reference:
        payment = Payment.query.filter_by(provider_reference=provider_reference).first()

    processing_status = WebhookProcessingStatus.IGNORED
    if payment is not None and event_type in ("payment.succeeded", "payment.failed"):
        if event_type == "payment.succeeded":
            confirm_payment_success(payment)
        else:
            mark_payment_failed(payment, payload.get("failure_reason") or "Payment failed (webhook).")
        processing_status = WebhookProcessingStatus.PROCESSED

    event = PaymentWebhookEvent(
        provider=provider_name,
        external_event_id=external_event_id,
        event_type=event_type,
        signature_verified=True,
        payload_reference=json.dumps(payload)[:2000],
        processing_status=processing_status,
        payment_id=payment.id if payment else None,
        processed_at=ledger_service.utcnow(),
    )
    db.session.add(event)
    db.session.commit()
    return {"status": "PROCESSED", "event": event.to_public_dict()}


# --- Lookups -----------------------------------------------------------

def get_owned_payment_or_404(customer, payment_public_id: str) -> Payment:
    payment = Payment.query.filter_by(public_id=payment_public_id, customer_id=customer.id).first()
    if payment is None:
        raise NotFoundError("Payment not found.")
    return payment


def get_any_payment_or_404(payment_public_id: str) -> Payment:
    payment = Payment.query.filter_by(public_id=payment_public_id).first()
    if payment is None:
        raise NotFoundError("Payment not found.")
    return payment


def list_payments_for_order(customer, order_public_id: str):
    order = get_owned_order_for_payment_or_404(customer, order_public_id)
    return order.payments.order_by(Payment.created_at.desc()).all()


def list_all_payments(status: str | None = None, page: int = 1, per_page: int = 20):
    query = Payment.query
    if status:
        query = query.filter(Payment.status == status)
    return query.order_by(Payment.created_at.desc()).paginate(
        page=max(page, 1), per_page=max(min(per_page, 100), 1), error_out=False
    )
