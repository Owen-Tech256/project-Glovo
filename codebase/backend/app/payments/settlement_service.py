"""
Settlement/earning recognition (SRS 14: "occurs only after the configured
business trigger, such as delivered/settled"). `settle_order` is called
exactly once, from app/logistics/delivery_service.py:complete_delivery,
the instant an order reaches DELIVERED - the same "separate commit, hook
off the state transition" pattern Phase 4 used for dispatch.

Split (see PHASE_5_NOTES.md for the full rationale):
    vendor_commission    = commission_service.calculate_commission(rule, order.subtotal)
    vendor_gross_earnings = order.subtotal - vendor_commission
    rider_earnings        = order.fees            (the delivery fee, passed through in full)
    platform_commission   = vendor_commission
    vendor_gross_earnings + rider_earnings + platform_commission == order.total, always -
    so the single PAYMENT_CAPTURE amount already collected is fully and
    exactly redistributed, balanced, in one settlement transaction.
"""
from app.extensions import db
from app.models.order import Order
from app.models.delivery import Delivery
from app.models.financial_account import FinancialAccountType, FinancialAccountOwnerType
from app.models.financial_transaction import FinancialTransactionType, FinancialReferenceType
from app.models.ledger_entry import LedgerEntryType
from app.models.commission_snapshot import CommissionSnapshot
from app.payments import ledger_service, commission_service, wallet_service, vendor_finance_service
from app.payments.ledger_service import LedgerLeg


def settle_order(order: Order) -> None:
    """Idempotent: a second call for an already-settled order is a no-op
    (guarded by ledger_service's own idempotency key on the settlement
    transaction, f"order_settlement:{order.id}"). Silently does nothing if
    the order was never paid (defensive only - DELIVERED is unreachable
    without PAYMENT_CONFIRMED via the order state machine) or has no rider
    assigned (should be equally unreachable, since a Delivery only reaches
    DELIVERED with a rider on it)."""
    existing = ledger_service.find_existing_transaction(
        FinancialTransactionType.ORDER_SETTLEMENT, f"order_settlement:{order.id}"
    )
    if existing is not None:
        return

    from app.models.payment import Payment, PaymentStatus

    payment = Payment.query.filter_by(order_id=order.id, status=PaymentStatus.SUCCEEDED).first()
    if payment is None:
        return

    delivery = Delivery.query.filter_by(order_id=order.id).first()
    if delivery is None or delivery.rider_id is None:
        return

    rule = commission_service.get_applicable_rule()
    # Phase 6: commission is calculated on the post-discount basis (SRS 4:
    # "Commission calculations use the configured post-discount financial
    # basis") - a promotion discount comes out of the vendor's own
    # earnings, not the platform's commission or the rider's delivery fee.
    # order.total already has discount_total subtracted (see
    # app/orders/service.py:create_order), so this keeps
    # vendor_gross_earnings + rider_earnings + platform_commission ==
    # order.total exactly, the same invariant this module's docstring
    # describes.
    discounted_subtotal = order.subtotal - (order.discount_total or 0)
    vendor_commission = commission_service.calculate_commission(rule, discounted_subtotal)
    vendor_gross_earnings = discounted_subtotal - vendor_commission
    rider_earnings = order.fees
    platform_commission = vendor_commission

    vendor = delivery.branch.vendor
    rider = delivery.rider

    platform_clearing = ledger_service.get_or_create_account(
        FinancialAccountType.PLATFORM_CLEARING, FinancialAccountOwnerType.PLATFORM
    )
    vendor_account = ledger_service.get_or_create_account(
        FinancialAccountType.VENDOR_PAYABLE, FinancialAccountOwnerType.VENDOR, owner_id=vendor.id
    )
    rider_account = ledger_service.get_or_create_account(
        FinancialAccountType.RIDER_PAYABLE, FinancialAccountOwnerType.RIDER, owner_id=rider.id
    )
    platform_revenue = ledger_service.get_or_create_account(
        FinancialAccountType.PLATFORM_REVENUE, FinancialAccountOwnerType.PLATFORM
    )

    legs = [
        LedgerLeg(platform_clearing, LedgerEntryType.DEBIT, order.total, description=f"Settlement for order {order.public_order_number}"),
    ]
    if vendor_gross_earnings > 0:
        legs.append(LedgerLeg(vendor_account, LedgerEntryType.CREDIT, vendor_gross_earnings, description="Vendor earnings"))
    if rider_earnings > 0:
        legs.append(LedgerLeg(rider_account, LedgerEntryType.CREDIT, rider_earnings, description="Rider earnings"))
    if platform_commission > 0:
        legs.append(LedgerLeg(platform_revenue, LedgerEntryType.CREDIT, platform_commission, description="Platform commission"))

    transaction, created = ledger_service.post_transaction(
        FinancialTransactionType.ORDER_SETTLEMENT,
        FinancialReferenceType.ORDER,
        order.id,
        legs,
        idempotency_key=f"order_settlement:{order.id}",
        description=f"Settlement for order {order.public_order_number}.",
    )
    if not created:
        return

    if vendor_gross_earnings > 0:
        vendor_account_row = vendor_finance_service.get_or_create_vendor_account(vendor)
        vendor_finance_service.credit_payable(vendor_account_row, vendor_gross_earnings)

    if rider_earnings > 0:
        wallet = wallet_service.get_or_create_wallet(rider)
        wallet_service.credit_earning(
            wallet, transaction.id, rider_earnings, description=f"Delivery earnings for order {order.public_order_number}"
        )

    db.session.add(
        CommissionSnapshot(
            financial_transaction_id=transaction.id,
            commission_rule_id=rule.id,
            rate_snapshot=rule.percentage_rate,
            fixed_snapshot=rule.fixed_amount,
            calculated_amount=platform_commission,
            currency=transaction.currency,
        )
    )

    db.session.commit()

    if rider_earnings > 0:
        from app.notifications.events import notify
        from app.models.notification import NotificationCategory

        notify(
            rider.user, NotificationCategory.PAYOUT, template_key="wallet_earning_posted",
            context={"amount": str(rider_earnings), "currency": transaction.currency, "order_number": order.public_order_number},
            entity_type="ORDER", entity_id=order.public_id,
        )
