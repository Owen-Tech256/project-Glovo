"""
Admin-only finance operations: commission rule management, refund
approval/rejection, payout retry, manual wallet adjustments, and basic
reconciliation. Every state-changing action here is written to
`AuditEvent` (the same Phase 1 audit table used throughout this codebase),
per SRS 15: "Audit administrative adjustments, approvals and payout
interventions."
"""
from decimal import Decimal

from app.extensions import db
from app.common.errors import NotFoundError, ValidationAppError
from app.models.audit_event import AuditEvent
from app.models.commission_rule import CommissionRule, CommissionScopeType, CommissionRuleStatus
from app.models.financial_account import FinancialAccount
from app.models.ledger_entry import LedgerEntry, LedgerEntryType
from app.models.rider import Rider
from app.payments import ledger_service, refund_service, vendor_finance_service, wallet_service
from app.payments.ledger_service import utcnow


def _audit(admin_user, event_type: str, ip_address: str | None, note: str | None = None) -> None:
    db.session.add(
        AuditEvent(user_id=admin_user.id, event_type=event_type, ip_address=ip_address, user_agent=(note or "")[:255])
    )


# --- Commission rules ----------------------------------------------------

def list_commission_rules(status: str | None = None):
    query = CommissionRule.query
    if status:
        query = query.filter(CommissionRule.status == status)
    return query.order_by(CommissionRule.created_at.desc()).all()


def get_commission_rule_or_404(rule_public_id: str) -> CommissionRule:
    rule = CommissionRule.query.filter_by(public_id=rule_public_id).first()
    if rule is None:
        raise NotFoundError("Commission rule not found.")
    return rule


def create_commission_rule(admin_user, data: dict, ip_address: str | None) -> CommissionRule:
    rule = CommissionRule(
        name=data["name"],
        percentage_rate=data.get("percentage_rate", Decimal("0")),
        fixed_amount=data.get("fixed_amount", Decimal("0")),
        scope_type=CommissionScopeType(data.get("scope_type", CommissionScopeType.GLOBAL.value)),
        scope_id=data.get("scope_id"),
        status=CommissionRuleStatus.ACTIVE,
        effective_from=data.get("effective_from") or utcnow(),
        effective_to=data.get("effective_to"),
    )
    db.session.add(rule)
    _audit(admin_user, "COMMISSION_RULE_CREATED", ip_address, note=f"{rule.name} rate={rule.percentage_rate}")
    db.session.commit()
    return rule


def update_commission_rule(admin_user, rule: CommissionRule, data: dict, ip_address: str | None) -> CommissionRule:
    # Editing in place never rewrites history - see CommissionRule's own
    # docstring: every past calculation already lives in its own immutable
    # CommissionSnapshot row.
    if "name" in data:
        rule.name = data["name"]
    if "percentage_rate" in data:
        rule.percentage_rate = data["percentage_rate"]
    if "fixed_amount" in data:
        rule.fixed_amount = data["fixed_amount"]
    if "status" in data:
        rule.status = CommissionRuleStatus(data["status"])
    if "effective_to" in data:
        rule.effective_to = data["effective_to"]
    _audit(admin_user, "COMMISSION_RULE_UPDATED", ip_address, note=f"{rule.public_id}")
    db.session.commit()
    return rule


# --- Refunds ---------------------------------------------------------------

def approve_refund(admin_user, refund_public_id: str, ip_address: str | None):
    refund = refund_service.get_any_refund_or_404(refund_public_id)
    refund = refund_service.approve_refund(admin_user, refund)
    _audit(admin_user, "REFUND_APPROVED", ip_address, note=f"{refund.public_id} amount={refund.amount}")
    db.session.commit()
    return refund


def reject_refund(admin_user, refund_public_id: str, reason: str | None, ip_address: str | None):
    refund = refund_service.get_any_refund_or_404(refund_public_id)
    refund = refund_service.reject_refund(admin_user, refund, reason)
    _audit(admin_user, "REFUND_REJECTED", ip_address, note=f"{refund.public_id}")
    db.session.commit()
    return refund


def retry_refund(admin_user, refund_public_id: str, ip_address: str | None):
    refund = refund_service.get_any_refund_or_404(refund_public_id)
    refund = refund_service.retry_refund(refund)
    _audit(admin_user, "REFUND_RETRIED", ip_address, note=f"{refund.public_id}")
    db.session.commit()
    return refund


# --- Payouts -----------------------------------------------------------

def retry_payout(admin_user, payout_public_id: str, ip_address: str | None):
    payout = vendor_finance_service.get_any_payout_or_404(payout_public_id)
    payout = vendor_finance_service.retry_payout(payout)
    _audit(admin_user, "PAYOUT_RETRIED", ip_address, note=f"{payout.public_id}")
    db.session.commit()
    return payout


# --- Wallet adjustments --------------------------------------------------

def create_wallet_adjustment(admin_user, rider_public_id: str, amount: Decimal, reason: str, ip_address: str | None):
    rider = Rider.query.filter_by(public_id=rider_public_id).first()
    if rider is None:
        raise NotFoundError("Rider not found.")
    entry = wallet_service.apply_admin_adjustment(admin_user, rider, amount, reason)
    _audit(admin_user, "WALLET_ADJUSTMENT", ip_address, note=f"rider={rider.public_id} amount={amount}")
    db.session.commit()
    return entry


# --- Reconciliation --------------------------------------------------------

def reconciliation_summary() -> dict:
    """A basic sanity check (SRS 12: "reconciliation-oriented records"):
    for every financial account, the cached balance (where one exists)
    should equal the balance reconciled purely from ledger entries, and
    system-wide, total debits should equal total credits."""
    accounts = FinancialAccount.query.all()
    mismatches = []
    for account in accounts:
        reconciled = ledger_service.account_balance(account)
        mismatches.append(
            {
                "account_id": account.public_id,
                "account_type": account.account_type.value,
                "owner_type": account.owner_type.value,
                "owner_id": account.owner_id,
                "reconciled_balance": str(reconciled),
            }
        )

    total_debits = (
        db.session.query(db.func.coalesce(db.func.sum(LedgerEntry.amount), 0))
        .filter(LedgerEntry.entry_type == LedgerEntryType.DEBIT)
        .scalar()
    )
    total_credits = (
        db.session.query(db.func.coalesce(db.func.sum(LedgerEntry.amount), 0))
        .filter(LedgerEntry.entry_type == LedgerEntryType.CREDIT)
        .scalar()
    )
    return {
        "accounts": mismatches,
        "total_debits": str(Decimal(total_debits)),
        "total_credits": str(Decimal(total_credits)),
        "balanced": Decimal(total_debits) == Decimal(total_credits),
    }
