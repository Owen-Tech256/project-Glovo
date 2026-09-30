"""
Vendor payable balance + payout workflow (SRS 9). Mirrors wallet_service's
role for riders: `VendorFinancialAccount` is a cached projection of the
vendor's VENDOR_PAYABLE ledger account, kept in lockstep with it.

Payout double-spend protection (implementation prompt 7/12) works in two
layers:
  1. At REQUEST time, `request_payout` row-locks the vendor account and
     checks the requested amount against (ledger balance - funds already
     committed to any non-terminal or PAID payout), so two concurrent
     requests can never both reserve the same money.
  2. The ledger-affecting DEBIT only ever posts once, the instant a payout
     first reaches PAID, guarded by ledger_service's own idempotency key
     (f"vendor_payout:{payout.id}") - so even a retried PROCESSING->PAID
     transition after a crash can never double-debit the vendor.
"""
from decimal import Decimal

from app.extensions import db
from app.common.errors import NotFoundError, ValidationAppError, ConflictError
from app.models.vendor import Vendor
from app.models.vendor_financial_account import VendorFinancialAccount, VendorAccountStatus
from app.models.vendor_payout import VendorPayout, VendorPayoutStatus
from app.models.financial_account import FinancialAccountType, FinancialAccountOwnerType
from app.models.financial_transaction import FinancialTransactionType, FinancialReferenceType
from app.models.ledger_entry import LedgerEntryType
from app.payments import ledger_service
from app.payments.ledger_service import LedgerLeg
from app.payments.providers import get_provider


# --- Account provisioning --------------------------------------------------

def get_or_create_vendor_account(vendor: Vendor) -> VendorFinancialAccount:
    account_row = VendorFinancialAccount.query.filter_by(vendor_id=vendor.id).first()
    if account_row is not None:
        return account_row

    ledger_account = ledger_service.get_or_create_account(
        FinancialAccountType.VENDOR_PAYABLE, FinancialAccountOwnerType.VENDOR, owner_id=vendor.id
    )
    account_row = VendorFinancialAccount(
        vendor_id=vendor.id,
        financial_account_id=ledger_account.id,
        currency=ledger_service.default_currency(),
        cached_payable_balance=Decimal("0"),
        status=VendorAccountStatus.ACTIVE,
    )
    db.session.add(account_row)
    db.session.flush()
    return account_row


def credit_payable(vendor_account: VendorFinancialAccount, amount: Decimal) -> None:
    """Called by settlement_service inside its own ledger-posting
    transaction - just keeps the cache in lockstep, does not post
    anything itself."""
    vendor_account.cached_payable_balance = vendor_account.cached_payable_balance + amount


def debit_payable(vendor_account: VendorFinancialAccount, amount: Decimal) -> None:
    """The mirror of credit_payable - called by app/advertising/service.py
    inside its own ledger-posting transaction when billing ad spend
    against a vendor's payable balance. Like credit_payable, this only
    keeps the cache in lockstep; it never posts a ledger entry itself, and
    is free to take the vendor's payable balance negative (a vendor who
    has spent more on ads than they've currently earned simply owes the
    platform - the next settlement replenishes it)."""
    vendor_account.cached_payable_balance = vendor_account.cached_payable_balance - amount


# --- Financial summary -------------------------------------------------

def get_financial_summary(vendor: Vendor) -> dict:
    account = get_or_create_vendor_account(vendor)
    committed = (
        VendorPayout.query.filter(
            VendorPayout.vendor_id == vendor.id,
            VendorPayout.status.in_(
                [VendorPayoutStatus.REQUESTED, VendorPayoutStatus.PROCESSING, VendorPayoutStatus.PAID]
            ),
        )
        .with_entities(db.func.coalesce(db.func.sum(VendorPayout.amount), 0))
        .scalar()
    )
    paid_total = (
        VendorPayout.query.filter(VendorPayout.vendor_id == vendor.id, VendorPayout.status == VendorPayoutStatus.PAID)
        .with_entities(db.func.coalesce(db.func.sum(VendorPayout.amount), 0))
        .scalar()
    )
    return {
        "account": account.to_public_dict(),
        "available_for_payout": str(max(account.cached_payable_balance - Decimal(committed), Decimal("0"))),
        "lifetime_paid_out": str(Decimal(paid_total)),
    }


# --- Payout lifecycle --------------------------------------------------

def _available_for_payout(vendor_account: VendorFinancialAccount) -> Decimal:
    """Ledger balance minus everything already committed to a non-terminal
    or PAID payout - the row-locked check that prevents double-spend at
    request time."""
    committed = (
        VendorPayout.query.filter(
            VendorPayout.vendor_account_id == vendor_account.id,
            VendorPayout.status.in_(
                [VendorPayoutStatus.REQUESTED, VendorPayoutStatus.PROCESSING, VendorPayoutStatus.PAID]
            ),
        )
        .with_entities(db.func.coalesce(db.func.sum(VendorPayout.amount), 0))
        .scalar()
    )
    return vendor_account.cached_payable_balance - Decimal(committed)


def request_payout(vendor: Vendor, amount: Decimal | None, destination_reference: str,
                    idempotency_key: str | None) -> tuple[VendorPayout, bool]:
    if idempotency_key:
        existing = VendorPayout.query.filter_by(vendor_id=vendor.id, idempotency_key=idempotency_key).first()
        if existing is not None:
            return existing, False

    vendor_account = get_or_create_vendor_account(vendor)
    # Row-lock: serializes concurrent payout requests against the same
    # vendor account, same pattern as orders/service.py's cart lock and
    # dispatch_service.py's delivery lock.
    vendor_account = VendorFinancialAccount.query.filter_by(id=vendor_account.id).with_for_update().first()

    available = _available_for_payout(vendor_account)
    requested_amount = amount if amount is not None else available
    if requested_amount is None or requested_amount <= 0:
        raise ValidationAppError("There are no payable funds available to pay out.", code="NO_PAYABLE_FUNDS")
    requested_amount = requested_amount.quantize(Decimal("0.01"))
    if requested_amount > available:
        raise ValidationAppError(
            "The requested payout amount exceeds your available payable balance.", code="INSUFFICIENT_PAYABLE_BALANCE"
        )

    payout = VendorPayout(
        vendor_id=vendor.id,
        vendor_account_id=vendor_account.id,
        amount=requested_amount,
        currency=vendor_account.currency,
        status=VendorPayoutStatus.REQUESTED,
        destination_reference=destination_reference,
        idempotency_key=idempotency_key,
        requested_at=ledger_service.utcnow(),
    )
    db.session.add(payout)
    db.session.commit()

    # This mock provider is synchronous, so a payout is attempted the
    # instant it's requested - see _attempt_processing's own docstring.
    return _attempt_processing(payout), True


def _post_payout_ledger(payout: VendorPayout) -> None:
    vendor_ledger_account = ledger_service.get_or_create_account(
        FinancialAccountType.VENDOR_PAYABLE, FinancialAccountOwnerType.VENDOR, owner_id=payout.vendor_id
    )
    settlement_account = ledger_service.get_or_create_account(
        FinancialAccountType.PLATFORM_PAYOUT_SETTLEMENT, FinancialAccountOwnerType.PLATFORM
    )
    legs = [
        LedgerLeg(vendor_ledger_account, LedgerEntryType.DEBIT, payout.amount, description=f"Payout {payout.public_id}"),
        LedgerLeg(settlement_account, LedgerEntryType.CREDIT, payout.amount, description=f"Payout {payout.public_id}"),
    ]
    _transaction, created = ledger_service.post_transaction(
        FinancialTransactionType.VENDOR_PAYOUT,
        FinancialReferenceType.VENDOR_PAYOUT,
        payout.id,
        legs,
        idempotency_key=f"vendor_payout:{payout.id}",
        description=f"Vendor payout {payout.public_id} paid.",
    )
    if created:
        payout.vendor_account.cached_payable_balance = payout.vendor_account.cached_payable_balance - payout.amount


def _attempt_processing(payout: VendorPayout) -> VendorPayout:
    """Moves a REQUESTED (or retried FAILED) payout through PROCESSING to
    PAID/FAILED via the provider adapter. The ledger DEBIT only ever posts
    on the transition INTO PAID (see _post_payout_ledger), so calling this
    again on an already-PAID payout is a safe no-op (implementation
    prompt 7: "Support safe retry of failed payouts")."""
    if payout.status == VendorPayoutStatus.PAID:
        return payout

    payout.status = VendorPayoutStatus.PROCESSING
    db.session.commit()

    from flask import current_app

    provider = get_provider(current_app.config.get("DEFAULT_PAYMENT_PROVIDER", "mock"))
    result = provider.payout(payout)

    if result.status == "PAID":
        payout.status = VendorPayoutStatus.PAID
        payout.provider_reference = result.provider_reference
        payout.processed_at = ledger_service.utcnow()
        payout.failure_reason = None
        _post_payout_ledger(payout)
    else:
        payout.status = VendorPayoutStatus.FAILED
        payout.provider_reference = result.provider_reference
        payout.failure_reason = result.failure_reason
        payout.processed_at = ledger_service.utcnow()

    db.session.commit()

    from app.notifications.events import notify
    from app.models.notification import NotificationCategory

    vendor = db.session.get(Vendor, payout.vendor_id)
    if payout.status == VendorPayoutStatus.PAID:
        notify(
            vendor.owner, NotificationCategory.PAYOUT, template_key="payout_paid",
            context={"amount": str(payout.amount), "currency": payout.currency},
            entity_type="VENDOR_PAYOUT", entity_id=payout.public_id,
        )
    elif payout.status == VendorPayoutStatus.FAILED:
        notify(
            vendor.owner, NotificationCategory.PAYOUT, template_key="payout_failed",
            context={"amount": str(payout.amount), "currency": payout.currency},
            entity_type="VENDOR_PAYOUT", entity_id=payout.public_id,
        )
    return payout


def retry_payout(payout: VendorPayout) -> VendorPayout:
    if payout.status != VendorPayoutStatus.FAILED:
        raise ValidationAppError("Only a failed payout can be retried.", code="PAYOUT_NOT_RETRYABLE")
    return _attempt_processing(payout)


def cancel_payout(payout: VendorPayout) -> VendorPayout:
    if payout.status not in (VendorPayoutStatus.REQUESTED,):
        raise ValidationAppError(
            "Only a payout that hasn't started processing can be cancelled.", code="PAYOUT_NOT_CANCELLABLE"
        )
    payout.status = VendorPayoutStatus.CANCELLED
    payout.processed_at = ledger_service.utcnow()
    db.session.commit()
    return payout


# --- Lookups -------------------------------------------------------------

def get_owned_payout_or_404(vendor: Vendor, payout_public_id: str) -> VendorPayout:
    payout = VendorPayout.query.filter_by(public_id=payout_public_id, vendor_id=vendor.id).first()
    if payout is None:
        raise NotFoundError("Payout not found.")
    return payout


def get_any_payout_or_404(payout_public_id: str) -> VendorPayout:
    payout = VendorPayout.query.filter_by(public_id=payout_public_id).first()
    if payout is None:
        raise NotFoundError("Payout not found.")
    return payout


def list_vendor_payouts(vendor: Vendor, page: int = 1, per_page: int = 20):
    return VendorPayout.query.filter_by(vendor_id=vendor.id).order_by(VendorPayout.requested_at.desc()).paginate(
        page=max(page, 1), per_page=max(min(per_page, 100), 1), error_out=False
    )


def list_all_payouts(status: str | None = None, page: int = 1, per_page: int = 20):
    query = VendorPayout.query
    if status:
        query = query.filter(VendorPayout.status == status)
    return query.order_by(VendorPayout.requested_at.desc()).paginate(
        page=max(page, 1), per_page=max(min(per_page, 100), 1), error_out=False
    )
