"""
Full/partial refunds (SRS 10). Concurrency-safe reservation model: a
refund's amount is reserved against the payment the instant it is
REQUESTED (under a row lock on the Payment), by counting every
REQUESTED/APPROVED/PROCESSING/SUCCEEDED refund as already-committed - not
just SUCCEEDED ones. This is a deliberate strengthening of SRS 10's literal
"minus previous successful refunds": counting only SUCCEEDED refunds at
request time would let two concurrent full-refund requests both be
accepted (neither is SUCCEEDED yet) and then both processed, jointly
refunding more than was ever captured - which the concurrency requirement
(implementation prompt 12: "Concurrent refunds must never exceed the
refundable amount") explicitly rules out. A refund that ends up
FAILED/REJECTED simply drops out of the "committed" set for whichever
request is considered next.
"""
from decimal import Decimal

from flask import current_app

from app.extensions import db
from app.common.errors import NotFoundError, ValidationAppError, ConflictError
from app.models.order import Order
from app.models.payment import Payment, PaymentStatus
from app.models.refund import Refund, RefundStatus
from app.models.financial_account import FinancialAccountType, FinancialAccountOwnerType
from app.models.financial_transaction import FinancialTransactionType, FinancialReferenceType
from app.models.ledger_entry import LedgerEntryType
from app.payments import ledger_service
from app.payments.ledger_service import LedgerLeg
from app.payments.providers import get_provider

_COMMITTED_STATUSES = (RefundStatus.REQUESTED, RefundStatus.APPROVED, RefundStatus.PROCESSING, RefundStatus.SUCCEEDED)


def _committed_amount(payment: Payment) -> Decimal:
    total = (
        Refund.query.filter(Refund.payment_id == payment.id, Refund.status.in_(_COMMITTED_STATUSES))
        .with_entities(db.func.coalesce(db.func.sum(Refund.amount), 0))
        .scalar()
    )
    return Decimal(total)


def get_refundable_amount(payment: Payment) -> Decimal:
    return payment.amount - _committed_amount(payment)


def request_refund(customer, order_public_id: str, amount: Decimal | None, reason: str,
                    idempotency_key: str | None) -> tuple[Refund, bool]:
    if idempotency_key:
        existing = Refund.query.filter_by(requested_by_user_id=customer.id, idempotency_key=idempotency_key).first()
        if existing is not None:
            return existing, False

    order = Order.query.filter_by(public_id=order_public_id, customer_id=customer.id).first()
    if order is None:
        raise NotFoundError("Order not found.")

    payment = Payment.query.filter_by(order_id=order.id, status=PaymentStatus.SUCCEEDED).first()
    if payment is None:
        raise ValidationAppError("This order has no successful payment to refund.", code="NO_PAYMENT_TO_REFUND")

    # Row-lock the payment: the serialization point that keeps concurrent
    # refund requests from jointly over-committing (see module docstring).
    payment = Payment.query.filter_by(id=payment.id).with_for_update().first()

    refundable = payment.amount - _committed_amount(payment)
    refund_amount = amount if amount is not None else refundable
    if refund_amount is None or refund_amount <= 0:
        raise ValidationAppError("There is nothing left to refund on this payment.", code="NOTHING_TO_REFUND")
    refund_amount = refund_amount.quantize(Decimal("0.01"))
    if refund_amount > refundable:
        raise ValidationAppError(
            "The requested refund amount exceeds what remains refundable on this payment.",
            code="REFUND_EXCEEDS_REFUNDABLE",
        )

    refund = Refund(
        payment_id=payment.id,
        order_id=order.id,
        amount=refund_amount,
        currency=payment.currency,
        reason=reason,
        status=RefundStatus.REQUESTED,
        requested_by_user_id=customer.id,
        idempotency_key=idempotency_key,
    )
    db.session.add(refund)
    db.session.commit()

    if not current_app.config.get("REFUND_REQUIRES_APPROVAL", True):
        refund = _approve(refund, approver=None)
        refund = _process(refund)

    return refund, True


def _approve(refund: Refund, approver) -> Refund:
    refund.status = RefundStatus.APPROVED
    refund.approved_by_user_id = approver.id if approver else None
    refund.approved_at = ledger_service.utcnow()
    db.session.commit()
    return refund


def approve_refund(admin_user, refund: Refund) -> Refund:
    if refund.status != RefundStatus.REQUESTED:
        raise ValidationAppError("Only a requested refund can be approved.", code="REFUND_NOT_PENDING")
    refund = _approve(refund, approver=admin_user)
    return _process(refund)


def reject_refund(admin_user, refund: Refund, reason: str | None) -> Refund:
    if refund.status != RefundStatus.REQUESTED:
        raise ValidationAppError("Only a requested refund can be rejected.", code="REFUND_NOT_PENDING")
    refund.status = RefundStatus.REJECTED
    refund.approved_by_user_id = admin_user.id
    refund.approved_at = ledger_service.utcnow()
    if reason:
        refund.failure_reason = reason
    db.session.commit()
    return refund


def _process(refund: Refund) -> Refund:
    refund.status = RefundStatus.PROCESSING
    db.session.commit()

    payment = refund.payment
    provider = get_provider(payment.provider)
    result = provider.refund(refund, payment)

    if result.status == "SUCCEEDED":
        refund.status = RefundStatus.SUCCEEDED
        refund.provider_reference = result.provider_reference
        refund.processed_at = ledger_service.utcnow()
        refund.failure_reason = None
        _post_refund_ledger(refund, payment)
        _sync_payment_refund_status(payment)
    else:
        refund.status = RefundStatus.FAILED
        refund.provider_reference = result.provider_reference
        refund.failure_reason = result.failure_reason
        refund.processed_at = ledger_service.utcnow()

    db.session.commit()

    if refund.status == RefundStatus.SUCCEEDED:
        from app.notifications.events import notify
        from app.models.notification import NotificationCategory

        notify(
            refund.order.customer, NotificationCategory.PAYMENT, template_key="refund_processed",
            context={"amount": str(refund.amount), "currency": refund.currency, "order_number": refund.order.public_order_number},
            entity_type="ORDER", entity_id=refund.order.public_id,
        )
    return refund


def retry_refund(refund: Refund) -> Refund:
    if refund.status != RefundStatus.FAILED:
        raise ValidationAppError("Only a failed refund can be retried.", code="REFUND_NOT_RETRYABLE")
    return _process(refund)


def _post_refund_ledger(refund: Refund, payment: Payment) -> None:
    """The mirror of a payment capture - reverses the customer-facing
    payment ledger impact only. Does not claw back any vendor/rider
    settlement already posted for this order (see module/service docstrings
    and PHASE_5_NOTES.md): clawing back funds already paid to a vendor or
    rider is a separate manual-adjustment concern (the admin wallet-
    adjustments endpoint exists for exactly that), not something a refund
    does automatically - doing so silently could otherwise drive a vendor
    or rider balance negative, which SRS 8 explicitly prohibits."""
    customer_account = ledger_service.get_or_create_account(
        FinancialAccountType.CUSTOMER_CLEARING, FinancialAccountOwnerType.CUSTOMER, owner_id=payment.customer_id
    )
    platform_account = ledger_service.get_or_create_account(
        FinancialAccountType.PLATFORM_CLEARING, FinancialAccountOwnerType.PLATFORM
    )
    legs = [
        LedgerLeg(platform_account, LedgerEntryType.DEBIT, refund.amount, description=f"Refund {refund.public_id}"),
        LedgerLeg(customer_account, LedgerEntryType.CREDIT, refund.amount, description=f"Refund {refund.public_id}"),
    ]
    ledger_service.post_transaction(
        FinancialTransactionType.REFUND,
        FinancialReferenceType.REFUND,
        refund.id,
        legs,
        idempotency_key=f"refund:{refund.id}",
        currency=refund.currency,
        description=f"Refund for order {refund.order.public_order_number}.",
    )


def _sync_payment_refund_status(payment: Payment) -> None:
    total_refunded = (
        Refund.query.filter(Refund.payment_id == payment.id, Refund.status == RefundStatus.SUCCEEDED)
        .with_entities(db.func.coalesce(db.func.sum(Refund.amount), 0))
        .scalar()
    )
    total_refunded = Decimal(total_refunded)
    if total_refunded >= payment.amount:
        payment.status = PaymentStatus.REFUNDED
    elif total_refunded > 0:
        payment.status = PaymentStatus.PARTIALLY_REFUNDED


# --- Lookups -----------------------------------------------------------

def list_refunds_for_order(customer, order_public_id: str):
    order = Order.query.filter_by(public_id=order_public_id, customer_id=customer.id).first()
    if order is None:
        raise NotFoundError("Order not found.")
    return order.refunds.order_by(Refund.created_at.desc()).all()


def list_refunds_for_order_any(order_public_id: str):
    order = Order.query.filter_by(public_id=order_public_id).first()
    if order is None:
        raise NotFoundError("Order not found.")
    return order.refunds.order_by(Refund.created_at.desc()).all()


def get_any_refund_or_404(refund_public_id: str) -> Refund:
    refund = Refund.query.filter_by(public_id=refund_public_id).first()
    if refund is None:
        raise NotFoundError("Refund not found.")
    return refund


def list_all_refunds(status: str | None = None, page: int = 1, per_page: int = 20):
    query = Refund.query
    if status:
        query = query.filter(Refund.status == status)
    return query.order_by(Refund.created_at.desc()).paginate(
        page=max(page, 1), per_page=max(min(per_page, 100), 1), error_out=False
    )
