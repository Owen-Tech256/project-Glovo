"""
The rider wallet (SRS 8) - a rider-facing cached projection of that
rider's RIDER_PAYABLE ledger account. Every function here that changes a
balance does so by posting a real ledger transaction first
(ledger_service.post_transaction) and only then updating the wallet's
cache + writing the matching WalletTransaction row, in the same DB
transaction, so the two can never drift out of sync mid-request.
"""
from decimal import Decimal

from app.extensions import db
from app.common.errors import NotFoundError, ValidationAppError
from app.models.rider import Rider
from app.models.rider_wallet import RiderWallet, RiderWalletStatus
from app.models.wallet_transaction import WalletTransaction, WalletTransactionType, WalletTransactionStatus
from app.models.financial_account import FinancialAccountType, FinancialAccountOwnerType
from app.models.financial_transaction import FinancialTransactionType, FinancialReferenceType
from app.models.ledger_entry import LedgerEntryType
from app.payments import ledger_service
from app.payments.ledger_service import LedgerLeg


def get_or_create_wallet(rider: Rider) -> RiderWallet:
    wallet = RiderWallet.query.filter_by(rider_id=rider.id).first()
    if wallet is not None:
        return wallet

    account = ledger_service.get_or_create_account(
        FinancialAccountType.RIDER_PAYABLE, FinancialAccountOwnerType.RIDER, owner_id=rider.id
    )
    wallet = RiderWallet(
        rider_id=rider.id,
        financial_account_id=account.id,
        currency=ledger_service.default_currency(),
        cached_available_balance=Decimal("0"),
        cached_pending_balance=Decimal("0"),
        status=RiderWalletStatus.ACTIVE,
    )
    db.session.add(wallet)
    db.session.flush()
    return wallet


def credit_earning(wallet: RiderWallet, financial_transaction_id: int, amount: Decimal, description: str) -> WalletTransaction:
    """Credits a delivery earning straight to the available balance - this
    phase has no external clearing hold (see RiderWallet's docstring)."""
    wallet.cached_available_balance = wallet.cached_available_balance + amount
    entry = WalletTransaction(
        wallet_id=wallet.id,
        financial_transaction_id=financial_transaction_id,
        type=WalletTransactionType.EARNING,
        amount=amount,
        currency=wallet.currency,
        status=WalletTransactionStatus.POSTED,
        description=description,
    )
    db.session.add(entry)
    return entry


def apply_admin_adjustment(
    admin_user, rider: Rider, amount: Decimal, reason: str
) -> WalletTransaction:
    """A manual admin credit (amount > 0) or debit (amount < 0) to a
    rider's wallet (SRS 8: "Support authorized admin adjustments through
    ledger entries and audit logs"), routed through the same ledger
    posting path as every other wallet movement. A debit can never take
    the wallet negative (SRS 8: "Prevent unauthorized negative balances")."""
    if amount == 0:
        raise ValidationAppError("Adjustment amount cannot be zero.", code="INVALID_ADJUSTMENT_AMOUNT")

    wallet = get_or_create_wallet(rider)
    # Row-lock the wallet so two concurrent debit adjustments (or a debit
    # racing a payout-in-progress) can never both pass the non-negative
    # check against a balance that is about to change out from under them.
    wallet = RiderWallet.query.filter_by(id=wallet.id).with_for_update().first()

    magnitude = abs(amount).quantize(Decimal("0.01"))
    is_credit = amount > 0

    if not is_credit and magnitude > wallet.cached_available_balance:
        raise ValidationAppError(
            "This adjustment would take the rider's wallet negative.", code="INSUFFICIENT_WALLET_BALANCE"
        )

    rider_account = ledger_service.get_or_create_account(
        FinancialAccountType.RIDER_PAYABLE, FinancialAccountOwnerType.RIDER, owner_id=rider.id
    )
    platform_account = ledger_service.get_or_create_account(
        FinancialAccountType.PLATFORM_REVENUE, FinancialAccountOwnerType.PLATFORM
    )

    idempotency_key = f"wallet_adjustment:{rider.id}:{ledger_service.utcnow().timestamp()}:{admin_user.id}"

    if is_credit:
        legs = [
            LedgerLeg(platform_account, LedgerEntryType.DEBIT, magnitude, description=reason),
            LedgerLeg(rider_account, LedgerEntryType.CREDIT, magnitude, description=reason),
        ]
    else:
        legs = [
            LedgerLeg(rider_account, LedgerEntryType.DEBIT, magnitude, description=reason),
            LedgerLeg(platform_account, LedgerEntryType.CREDIT, magnitude, description=reason),
        ]

    transaction, _created = ledger_service.post_transaction(
        FinancialTransactionType.WALLET_ADJUSTMENT,
        FinancialReferenceType.WALLET_ADJUSTMENT,
        wallet.id,
        legs,
        idempotency_key=idempotency_key,
        description=f"Admin adjustment by {admin_user.public_id}: {reason}",
    )

    wallet.cached_available_balance = (
        wallet.cached_available_balance + magnitude if is_credit else wallet.cached_available_balance - magnitude
    )
    entry = WalletTransaction(
        wallet_id=wallet.id,
        financial_transaction_id=transaction.id,
        type=WalletTransactionType.ADJUSTMENT_CREDIT if is_credit else WalletTransactionType.ADJUSTMENT_DEBIT,
        amount=magnitude,
        currency=wallet.currency,
        status=WalletTransactionStatus.POSTED,
        description=reason,
    )
    db.session.add(entry)
    db.session.commit()
    return entry


def get_owned_wallet_or_404(rider: Rider) -> RiderWallet:
    wallet = get_or_create_wallet(rider)
    if wallet is None:
        raise NotFoundError("Wallet not found.")
    return wallet


def list_transactions(wallet: RiderWallet, page: int = 1, per_page: int = 20):
    return wallet.transactions.paginate(
        page=max(page, 1), per_page=max(min(per_page, 100), 1), error_out=False
    )
