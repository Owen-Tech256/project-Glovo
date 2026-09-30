"""
The append-only double-entry ledger (SRS 11/13/14) that every other Phase 5
service posts through. Nothing outside this module ever creates a
FinancialTransaction or LedgerEntry row directly, so "every posted
financial transaction is balanced" (implementation prompt 5) is guaranteed
in exactly one place.

Financial account model (see app/models/financial_account.py for the full
account-type list): a payment capture debits a per-customer memo
CUSTOMER_CLEARING account and credits the singleton PLATFORM_CLEARING
account; settlement at delivery debits PLATFORM_CLEARING and credits
VENDOR_PAYABLE + RIDER_PAYABLE + PLATFORM_REVENUE for the same total,
balanced; a refund is the mirror of a capture; a payout debits
VENDOR_PAYABLE and credits PLATFORM_PAYOUT_SETTLEMENT. This is a
deliberately simplified internal ledger, not a GAAP general ledger -
advanced accounting integration is explicitly out of scope (SRS 3).
"""
from datetime import datetime, timezone
from decimal import Decimal

from flask import current_app

from app.extensions import db
from app.common.errors import ValidationAppError
from app.models.financial_account import (
    FinancialAccount, FinancialAccountType, FinancialAccountOwnerType, FinancialAccountStatus,
)
from app.models.financial_transaction import (
    FinancialTransaction, FinancialTransactionType, FinancialReferenceType, FinancialTransactionStatus,
)
from app.models.ledger_entry import LedgerEntry, LedgerEntryType


class LedgerLeg:
    """One requested leg of a to-be-posted FinancialTransaction: which
    account, DEBIT or CREDIT, how much, and an optional human-readable
    description for that specific entry."""

    __slots__ = ("account", "entry_type", "amount", "description")

    def __init__(self, account: FinancialAccount, entry_type: LedgerEntryType, amount: Decimal, description: str | None = None):
        self.account = account
        self.entry_type = entry_type
        self.amount = amount
        self.description = description


def default_currency() -> str:
    return current_app.config.get("DEFAULT_CURRENCY", "USD")


def get_or_create_account(
    account_type: FinancialAccountType, owner_type: FinancialAccountOwnerType,
    owner_id: int | None = None, currency: str | None = None,
) -> FinancialAccount:
    """Lazily provisions the singleton PLATFORM_* accounts and per-owner
    CUSTOMER/VENDOR/RIDER accounts alike - one lookup pattern for both,
    matching the get_or_create_rider/get_or_create_vendor convention used
    everywhere else in this codebase."""
    currency = currency or default_currency()
    account = FinancialAccount.query.filter_by(
        account_type=account_type, owner_type=owner_type, owner_id=owner_id, currency=currency
    ).first()
    if account is not None:
        return account

    account = FinancialAccount(
        account_type=account_type, owner_type=owner_type, owner_id=owner_id,
        currency=currency, status=FinancialAccountStatus.ACTIVE,
    )
    db.session.add(account)
    try:
        db.session.flush()
    except Exception:
        db.session.rollback()
        account = FinancialAccount.query.filter_by(
            account_type=account_type, owner_type=owner_type, owner_id=owner_id, currency=currency
        ).first()
        if account is None:
            raise
    return account


def find_existing_transaction(transaction_type: FinancialTransactionType, idempotency_key: str) -> FinancialTransaction | None:
    """The ledger's own idempotency guard, independent of whatever
    idempotency mechanism the calling service (Payment/Refund/Payout) uses
    on top of it - see FinancialTransaction.idempotency_key's docstring."""
    return FinancialTransaction.query.filter_by(type=transaction_type, idempotency_key=idempotency_key).first()


def post_transaction(
    transaction_type: FinancialTransactionType,
    reference_type: FinancialReferenceType,
    reference_id: int,
    legs: list[LedgerLeg],
    idempotency_key: str,
    currency: str | None = None,
    description: str | None = None,
) -> tuple[FinancialTransaction, bool]:
    """Posts one balanced financial transaction and its ledger entries.
    Returns (transaction, was_created) - was_created is False when a
    transaction with this (type, idempotency_key) already exists, in which
    case NOTHING is written and the existing row is returned unchanged.
    This is the single choke point that makes "two identical payment
    confirmations result in one financial posting" true (implementation
    prompt 12), as long as every caller derives idempotency_key
    deterministically from the business event (e.g. f"payment:{payment.id}"),
    which every Phase 5 service in this codebase does.

    Does not commit - callers control the transaction boundary, same
    convention as app/orders/state_machine.py:apply_transition.
    """
    existing = find_existing_transaction(transaction_type, idempotency_key)
    if existing is not None:
        return existing, False

    currency = currency or default_currency()
    if any(leg.amount <= 0 for leg in legs):
        raise ValidationAppError("Ledger entries must have a positive amount.", code="INVALID_LEDGER_AMOUNT")

    debit_total = sum((leg.amount for leg in legs if leg.entry_type == LedgerEntryType.DEBIT), Decimal("0"))
    credit_total = sum((leg.amount for leg in legs if leg.entry_type == LedgerEntryType.CREDIT), Decimal("0"))
    if debit_total != credit_total:
        raise ValidationAppError(
            f"Ledger postings must balance (debits={debit_total}, credits={credit_total}).",
            code="UNBALANCED_LEDGER_TRANSACTION",
        )

    transaction = FinancialTransaction(
        type=transaction_type,
        reference_type=reference_type,
        reference_id=reference_id,
        status=FinancialTransactionStatus.POSTED,
        idempotency_key=idempotency_key,
        currency=currency,
        description=description,
    )
    db.session.add(transaction)
    db.session.flush()  # obtain transaction.id for the entries below

    for leg in legs:
        db.session.add(
            LedgerEntry(
                financial_transaction_id=transaction.id,
                account_id=leg.account.id,
                entry_type=leg.entry_type,
                amount=leg.amount,
                currency=currency,
                description=leg.description,
            )
        )

    return transaction, True


def account_balance(account: FinancialAccount) -> Decimal:
    """Reconciles a balance directly from ledger_entries (SRS 5: "must
    always be reconcilable from ledger entries") - CREDIT increases the
    balance, DEBIT decreases it, for every account type in this ledger
    (see module docstring for why that convention is self-consistent
    across clearing/payable/revenue accounts alike)."""
    credit_sum = (
        db.session.query(db.func.coalesce(db.func.sum(LedgerEntry.amount), 0))
        .filter(LedgerEntry.account_id == account.id, LedgerEntry.entry_type == LedgerEntryType.CREDIT)
        .scalar()
    )
    debit_sum = (
        db.session.query(db.func.coalesce(db.func.sum(LedgerEntry.amount), 0))
        .filter(LedgerEntry.account_id == account.id, LedgerEntry.entry_type == LedgerEntryType.DEBIT)
        .scalar()
    )
    return Decimal(credit_sum) - Decimal(debit_sum)


def utcnow():
    return datetime.now(timezone.utc)
