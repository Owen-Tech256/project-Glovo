"""
Commission rule selection and calculation (SRS 7). Only GLOBAL-scoped
rules are ever selected in this phase - VENDOR/CATEGORY scoping is modeled
on CommissionRule (scope_type/scope_id) but deliberately not resolved here
yet, per that field's own docstring.
"""
from datetime import timezone
from decimal import Decimal, ROUND_HALF_UP

from flask import current_app

from app.extensions import db
from app.models.base import to_aware_utc
from app.models.commission_rule import CommissionRule, CommissionScopeType, CommissionRuleStatus
from app.payments.ledger_service import utcnow


def _quantize(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def get_applicable_rule() -> CommissionRule:
    """Returns the currently-effective GLOBAL commission rule, lazily
    bootstrapping one from PLATFORM_COMMISSION_PERCENTAGE_DEFAULT if an
    admin has never configured one (see app/config.py) - settlement must
    never fail just because the marketplace hasn't been configured yet.
    If several GLOBAL ACTIVE rules are somehow effective at once, the most
    recently created one wins (an admin creating a new rule is assumed to
    supersede the old one, even though PATCHing the old one directly, or
    setting its effective_to, is the normal way to retire it)."""
    now = utcnow()
    rule = (
        CommissionRule.query.filter(
            CommissionRule.scope_type == CommissionScopeType.GLOBAL,
            CommissionRule.status == CommissionRuleStatus.ACTIVE,
        )
        .order_by(CommissionRule.created_at.desc())
        .all()
    )
    for candidate in rule:
        effective_from = to_aware_utc(candidate.effective_from)
        effective_to = to_aware_utc(candidate.effective_to)
        if effective_from is not None and effective_from > now:
            continue
        if effective_to is not None and effective_to <= now:
            continue
        return candidate

    return _bootstrap_default_rule()


def _bootstrap_default_rule() -> CommissionRule:
    default_rate = Decimal(str(current_app.config.get("PLATFORM_COMMISSION_PERCENTAGE_DEFAULT", "0.15")))
    rule = CommissionRule(
        name="Default platform commission",
        percentage_rate=default_rate,
        fixed_amount=Decimal("0"),
        scope_type=CommissionScopeType.GLOBAL,
        status=CommissionRuleStatus.ACTIVE,
        effective_from=utcnow(),
    )
    db.session.add(rule)
    db.session.flush()
    return rule


def calculate_commission(rule: CommissionRule, vendor_subtotal: Decimal) -> Decimal:
    """Commission is charged against the vendor's product subtotal only
    (never the delivery fee, which is passed through to the rider in full -
    see app/payments/settlement_service.py for the full split and its
    rationale)."""
    amount = (vendor_subtotal * rule.percentage_rate) + rule.fixed_amount
    if amount < 0:
        amount = Decimal("0")
    if amount > vendor_subtotal:
        amount = vendor_subtotal
    return _quantize(amount)
