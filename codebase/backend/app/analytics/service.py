"""
Read-only analytics/reporting (SRS 9). Every function here computes its
numbers fresh, directly from the authoritative Phase 1-6 tables (Order,
Payment, FinancialTransaction/LedgerEntry, Delivery, Refund, VendorPayout,
Review, Promotion/AdCampaign, SupportTicket/Dispute) via aggregate SQL
queries - nothing is cached or duplicated into a separate analytics table
(implementation prompt 5: "Avoid conflicting duplicate business totals").
This does mean a very large dataset would eventually want materialized
read models; that tradeoff is out of scope for this phase (SRS 3: "Full
enterprise data warehouse" is explicitly out of scope) and is noted in
PHASE_7_NOTES.md.

`_parse_date`/date filtering is intentionally simple (inclusive UTC day
boundaries) - no timezone-aware business-calendar logic, matching the
single-currency/no-multi-region-scope precedent set by Phase 5.
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.extensions import db
from app.models.order import Order, OrderStatus
from app.models.payment import Payment, PaymentStatus
from app.models.refund import Refund, RefundStatus
from app.models.financial_transaction import FinancialTransaction, FinancialTransactionType, FinancialTransactionStatus
from app.models.financial_account import FinancialAccount, FinancialAccountType
from app.models.ledger_entry import LedgerEntry, LedgerEntryType
from app.models.vendor_payout import VendorPayout, VendorPayoutStatus
from app.models.delivery import Delivery, DeliveryStatus
from app.models.delivery_assignment import DeliveryAssignment, DeliveryAssignmentStatus
from app.models.branch import Branch
from app.models.vendor import Vendor
from app.models.rider import Rider
from app.models.user import User, UserRole
from app.models.promotion import Promotion, PromotionUsage, PromotionUsageStatus
from app.models.ad_campaign import AdCampaign
from app.models.ad_event import AdEvent, AdEventType
from app.models.support_ticket import SupportTicket, TicketStatus
from app.models.dispute import Dispute, DisputeStatus


def _parse_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def resolve_range(date_from: str | None, date_to: str | None) -> tuple[datetime, datetime]:
    end = _parse_date(date_to) or datetime.now(timezone.utc)
    start = _parse_date(date_from) or (end - timedelta(days=30))
    # Make `date_to` an inclusive whole day when given only a date.
    if date_to and len(date_to) <= 10:
        end = end + timedelta(days=1)
    return start, end


def _num(value) -> str:
    if value is None:
        return "0.00"
    return str(Decimal(value).quantize(Decimal("0.01")))


def _count(query) -> int:
    return query.with_entities(db.func.count()).scalar() or 0


def _sum(query, column) -> Decimal:
    return Decimal(query.with_entities(db.func.coalesce(db.func.sum(column), 0)).scalar() or 0)


# --- Orders ----------------------------------------------------------------

def orders_metrics(date_from: str | None = None, date_to: str | None = None,
                    branch_public_id: str | None = None) -> dict:
    start, end = resolve_range(date_from, date_to)
    query = Order.query.filter(Order.created_at >= start, Order.created_at < end)
    if branch_public_id:
        branch = Branch.query.filter_by(public_id=branch_public_id).first()
        query = query.filter(Order.branch_id == (branch.id if branch else -1))

    total = _count(query)
    by_status = dict(
        query.with_entities(Order.status, db.func.count()).group_by(Order.status).all()
    )
    by_status = {(k.value if hasattr(k, "value") else k): v for k, v in by_status.items()}
    delivered = by_status.get(OrderStatus.DELIVERED.value, 0)
    cancelled = by_status.get(OrderStatus.CANCELLED.value, 0)
    gross = _sum(query.filter(Order.status != OrderStatus.CANCELLED), Order.total)
    aov = (gross / (total - cancelled)) if (total - cancelled) > 0 else Decimal("0")

    return {
        "date_from": start.isoformat(), "date_to": end.isoformat(),
        "total_orders": total,
        "orders_by_status": by_status,
        "delivered_orders": delivered,
        "cancelled_orders": cancelled,
        "completion_rate": round(delivered / total, 4) if total else 0,
        "cancellation_rate": round(cancelled / total, 4) if total else 0,
        "gross_order_value": _num(gross),
        "average_order_value": _num(aov),
    }


# --- Finance -----------------------------------------------------------

def finance_metrics(date_from: str | None = None, date_to: str | None = None) -> dict:
    start, end = resolve_range(date_from, date_to)

    payments = Payment.query.filter(Payment.created_at >= start, Payment.created_at < end)
    total_payments = _count(payments)
    succeeded_payments = _count(payments.filter(Payment.status == PaymentStatus.SUCCEEDED))
    gross_revenue = _sum(payments.filter(Payment.status == PaymentStatus.SUCCEEDED), Payment.amount)

    refunds = Refund.query.filter(Refund.created_at >= start, Refund.created_at < end)
    total_refunded = _sum(refunds.filter(Refund.status == RefundStatus.SUCCEEDED), Refund.amount)

    commission = _sum(
        FinancialTransaction.query.filter(
            FinancialTransaction.type == FinancialTransactionType.ORDER_SETTLEMENT,
            FinancialTransaction.status == FinancialTransactionStatus.POSTED,
            FinancialTransaction.created_at >= start, FinancialTransaction.created_at < end,
        ).join(LedgerEntry, LedgerEntry.financial_transaction_id == FinancialTransaction.id)
        .join(FinancialAccount, LedgerEntry.account_id == FinancialAccount.id)
        .filter(FinancialAccount.account_type == FinancialAccountType.PLATFORM_REVENUE,
                LedgerEntry.entry_type == LedgerEntryType.CREDIT),
        LedgerEntry.amount,
    )
    ad_revenue = _sum(
        FinancialTransaction.query.filter(
            FinancialTransaction.type == FinancialTransactionType.AD_SPEND,
            FinancialTransaction.created_at >= start, FinancialTransaction.created_at < end,
        ).join(LedgerEntry, LedgerEntry.financial_transaction_id == FinancialTransaction.id)
        .join(FinancialAccount, LedgerEntry.account_id == FinancialAccount.id)
        .filter(FinancialAccount.account_type == FinancialAccountType.PLATFORM_AD_REVENUE,
                LedgerEntry.entry_type == LedgerEntryType.CREDIT),
        LedgerEntry.amount,
    )

    payouts = VendorPayout.query.filter(VendorPayout.created_at >= start, VendorPayout.created_at < end)
    payouts_paid = _sum(payouts.filter(VendorPayout.status == VendorPayoutStatus.PAID), VendorPayout.amount)

    rider_earnings = _sum(
        FinancialTransaction.query.filter(
            FinancialTransaction.type == FinancialTransactionType.ORDER_SETTLEMENT,
            FinancialTransaction.status == FinancialTransactionStatus.POSTED,
            FinancialTransaction.created_at >= start, FinancialTransaction.created_at < end,
        ).join(LedgerEntry, LedgerEntry.financial_transaction_id == FinancialTransaction.id)
        .join(FinancialAccount, LedgerEntry.account_id == FinancialAccount.id)
        .filter(FinancialAccount.account_type == FinancialAccountType.RIDER_PAYABLE,
                LedgerEntry.entry_type == LedgerEntryType.CREDIT),
        LedgerEntry.amount,
    )

    return {
        "date_from": start.isoformat(), "date_to": end.isoformat(),
        "total_payment_attempts": total_payments,
        "successful_payments": succeeded_payments,
        "payment_success_rate": round(succeeded_payments / total_payments, 4) if total_payments else 0,
        "gross_revenue": _num(gross_revenue),
        "platform_commission_revenue": _num(commission),
        "platform_ad_revenue": _num(ad_revenue),
        "total_refunded": _num(total_refunded),
        "vendor_payouts_paid": _num(payouts_paid),
        "rider_earnings_accrued": _num(rider_earnings),
        "net_platform_revenue": _num(commission + ad_revenue),
    }


# --- Vendors -----------------------------------------------------------

def vendor_metrics(date_from: str | None = None, date_to: str | None = None,
                    vendor_public_id: str | None = None) -> dict:
    start, end = resolve_range(date_from, date_to)

    query = (
        db.session.query(
            Vendor.id, Vendor.public_id, Vendor.name,
            db.func.count(Order.id).label("order_count"),
            db.func.coalesce(db.func.sum(Order.total), 0).label("gross_sales"),
            db.func.coalesce(db.func.sum(Order.discount_total), 0).label("discounts"),
        )
        .join(Branch, Branch.vendor_id == Vendor.id)
        .join(Order, Order.branch_id == Branch.id)
        .filter(Order.created_at >= start, Order.created_at < end, Order.status != OrderStatus.CANCELLED)
        .group_by(Vendor.id, Vendor.public_id, Vendor.name)
    )
    if vendor_public_id:
        query = query.filter(Vendor.public_id == vendor_public_id)

    rows = query.order_by(db.desc("gross_sales")).limit(50).all()
    refunds_by_vendor = dict(
        db.session.query(Vendor.public_id, db.func.coalesce(db.func.sum(Refund.amount), 0))
        .join(Branch, Branch.vendor_id == Vendor.id).join(Order, Order.branch_id == Branch.id)
        .join(Refund, Refund.order_id == Order.id)
        .filter(Refund.status == RefundStatus.SUCCEEDED, Refund.created_at >= start, Refund.created_at < end)
        .group_by(Vendor.public_id).all()
    )

    vendors = []
    for row in rows:
        refunds = Decimal(refunds_by_vendor.get(row.public_id, 0))
        net_sales = Decimal(row.gross_sales) - refunds
        vendors.append({
            "vendor_id": row.public_id,
            "vendor_name": row.name,
            "order_count": row.order_count,
            "gross_sales": _num(row.gross_sales),
            "discounts": _num(row.discounts),
            "refunds": _num(refunds),
            "net_sales": _num(net_sales),
            "average_order_value": _num(Decimal(row.gross_sales) / row.order_count) if row.order_count else "0.00",
        })

    return {"date_from": start.isoformat(), "date_to": end.isoformat(), "vendors": vendors}


# --- Riders ------------------------------------------------------------

def rider_metrics(date_from: str | None = None, date_to: str | None = None,
                   rider_public_id: str | None = None) -> dict:
    start, end = resolve_range(date_from, date_to)

    query = (
        db.session.query(
            Rider.id, Rider.public_id, Rider.rating_average,
            db.func.count(Delivery.id).label("completed_deliveries"),
        )
        .join(Delivery, Delivery.rider_id == Rider.id)
        .filter(Delivery.status == DeliveryStatus.DELIVERED, Delivery.delivered_at >= start, Delivery.delivered_at < end)
        .group_by(Rider.id, Rider.public_id, Rider.rating_average)
    )
    if rider_public_id:
        query = query.filter(Rider.public_id == rider_public_id)
    rows = query.order_by(db.desc("completed_deliveries")).limit(50).all()

    accept_reject = (
        db.session.query(Rider.public_id, DeliveryAssignment.status, db.func.count())
        .join(DeliveryAssignment, DeliveryAssignment.rider_id == Rider.id)
        .filter(DeliveryAssignment.offered_at >= start, DeliveryAssignment.offered_at < end)
        .group_by(Rider.public_id, DeliveryAssignment.status).all()
    )
    by_rider_assignments: dict[str, dict[str, int]] = {}
    for public_id, status, cnt in accept_reject:
        by_rider_assignments.setdefault(public_id, {})[status.value if hasattr(status, "value") else status] = cnt

    earnings_by_rider = dict(
        db.session.query(Rider.public_id, db.func.coalesce(db.func.sum(LedgerEntry.amount), 0))
        .join(FinancialAccount, db.and_(
            FinancialAccount.account_type == FinancialAccountType.RIDER_PAYABLE,
            FinancialAccount.owner_id == Rider.id,
        ))
        .join(LedgerEntry, db.and_(
            LedgerEntry.account_id == FinancialAccount.id,
            LedgerEntry.entry_type == LedgerEntryType.CREDIT,
            LedgerEntry.created_at >= start, LedgerEntry.created_at < end,
        ))
        .group_by(Rider.public_id).all()
    )

    riders = []
    for row in rows:
        assignments = by_rider_assignments.get(row.public_id, {})
        offered = sum(assignments.values())
        accepted = assignments.get("ACCEPTED", 0)
        rejected = assignments.get("REJECTED", 0)
        riders.append({
            "rider_id": row.public_id,
            "rating_average": str(row.rating_average) if row.rating_average is not None else None,
            "completed_deliveries": row.completed_deliveries,
            "offers_received": offered,
            "acceptance_rate": round(accepted / offered, 4) if offered else 0,
            "rejection_rate": round(rejected / offered, 4) if offered else 0,
            "earnings": _num(earnings_by_rider.get(row.public_id, 0)),
        })

    return {"date_from": start.isoformat(), "date_to": end.isoformat(), "riders": riders}


# --- Delivery ------------------------------------------------------------

def delivery_metrics(date_from: str | None = None, date_to: str | None = None) -> dict:
    start, end = resolve_range(date_from, date_to)
    query = Delivery.query.filter(Delivery.created_at >= start, Delivery.created_at < end)
    total = _count(query)
    delivered = query.filter(Delivery.status == DeliveryStatus.DELIVERED,
                              Delivery.assigned_at.isnot(None), Delivery.picked_up_at.isnot(None)).all()
    cancelled = _count(query.filter(Delivery.status == DeliveryStatus.CANCELLED))

    def _avg_seconds(pairs: list[tuple[datetime, datetime]]) -> float | None:
        deltas = [(b - a).total_seconds() for a, b in pairs if a and b]
        return round(sum(deltas) / len(deltas), 1) if deltas else None

    assignment_times = _avg_seconds([(d.created_at, d.assigned_at) for d in delivered])
    pickup_times = _avg_seconds([(d.assigned_at, d.picked_up_at) for d in delivered])
    full_duration = _avg_seconds([(d.created_at, d.delivered_at) for d in delivered])

    return {
        "date_from": start.isoformat(), "date_to": end.isoformat(),
        "total_deliveries": total,
        "completed_deliveries": len(delivered),
        "cancelled_deliveries": cancelled,
        "failure_rate": round(cancelled / total, 4) if total else 0,
        "avg_assignment_seconds": assignment_times,
        "avg_pickup_seconds": pickup_times,
        "avg_total_duration_seconds": full_duration,
    }


# --- Customers -----------------------------------------------------------

def customer_metrics(date_from: str | None = None, date_to: str | None = None) -> dict:
    start, end = resolve_range(date_from, date_to)
    registrations = _count(User.query.filter(
        User.role == UserRole.CUSTOMER, User.created_at >= start, User.created_at < end
    ))

    order_counts = dict(
        db.session.query(Order.customer_id, db.func.count())
        .filter(Order.created_at >= start, Order.created_at < end, Order.status != OrderStatus.CANCELLED)
        .group_by(Order.customer_id).all()
    )
    active_customers = len(order_counts)
    repeat_customers = sum(1 for c in order_counts.values() if c > 1)
    total_orders = sum(order_counts.values())

    return {
        "date_from": start.isoformat(), "date_to": end.isoformat(),
        "new_registrations": registrations,
        "active_customers": active_customers,
        "repeat_customers": repeat_customers,
        "repeat_rate": round(repeat_customers / active_customers, 4) if active_customers else 0,
        "average_orders_per_active_customer": round(total_orders / active_customers, 2) if active_customers else 0,
    }


# --- Promotions / advertising --------------------------------------------

def promotion_ad_metrics(date_from: str | None = None, date_to: str | None = None) -> dict:
    start, end = resolve_range(date_from, date_to)

    usages = PromotionUsage.query.filter(
        PromotionUsage.status == PromotionUsageStatus.CONSUMED,
        PromotionUsage.created_at >= start, PromotionUsage.created_at < end,
    )
    promo_usage_count = _count(usages)
    promo_discount_total = _sum(usages, PromotionUsage.discount_amount)
    active_promotions = _count(Promotion.query.filter(Promotion.status == "ACTIVE"))

    events = AdEvent.query.filter(AdEvent.occurred_at >= start, AdEvent.occurred_at < end)
    impressions = _count(events.filter(AdEvent.event_type == AdEventType.IMPRESSION))
    clicks = _count(events.filter(AdEvent.event_type == AdEventType.CLICK))
    spend = _sum(events, AdEvent.billed_amount)
    active_campaigns = _count(AdCampaign.query.filter(AdCampaign.status == "ACTIVE"))

    return {
        "date_from": start.isoformat(), "date_to": end.isoformat(),
        "active_promotions": active_promotions,
        "promotion_redemptions": promo_usage_count,
        "promotion_discount_total": _num(promo_discount_total),
        "active_ad_campaigns": active_campaigns,
        "ad_impressions": impressions,
        "ad_clicks": clicks,
        "ad_ctr": round(clicks / impressions, 4) if impressions else 0,
        "ad_spend": _num(spend),
    }


# --- Support / disputes --------------------------------------------------

def support_dispute_metrics(date_from: str | None = None, date_to: str | None = None) -> dict:
    start, end = resolve_range(date_from, date_to)

    tickets = SupportTicket.query.filter(SupportTicket.created_at >= start, SupportTicket.created_at < end)
    total_tickets = _count(tickets)
    tickets_by_status = dict(
        tickets.with_entities(SupportTicket.status, db.func.count()).group_by(SupportTicket.status).all()
    )
    tickets_by_status = {(k.value if hasattr(k, "value") else k): v for k, v in tickets_by_status.items()}
    tickets_by_category = dict(
        tickets.with_entities(SupportTicket.category, db.func.count()).group_by(SupportTicket.category).all()
    )
    tickets_by_category = {(k.value if hasattr(k, "value") else k): v for k, v in tickets_by_category.items()}
    resolved = tickets.filter(SupportTicket.resolved_at.isnot(None)).all()
    resolution_seconds = [
        (t.resolved_at - t.created_at).total_seconds() for t in resolved if t.resolved_at and t.created_at
    ]
    avg_resolution = round(sum(resolution_seconds) / len(resolution_seconds), 1) if resolution_seconds else None
    backlog = _count(SupportTicket.query.filter(SupportTicket.status.in_(
        [TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.WAITING_FOR_CUSTOMER]
    )))

    disputes = Dispute.query.filter(Dispute.created_at >= start, Dispute.created_at < end)
    total_disputes = _count(disputes)
    disputes_by_status = dict(
        disputes.with_entities(Dispute.status, db.func.count()).group_by(Dispute.status).all()
    )
    disputes_by_status = {(k.value if hasattr(k, "value") else k): v for k, v in disputes_by_status.items()}
    disputes_by_category = dict(
        disputes.with_entities(Dispute.category, db.func.count()).group_by(Dispute.category).all()
    )
    disputes_by_category = {(k.value if hasattr(k, "value") else k): v for k, v in disputes_by_category.items()}
    resolved_disputes = disputes.filter(Dispute.resolved_at.isnot(None)).all()
    dispute_resolution_seconds = [
        (d.resolved_at - d.created_at).total_seconds() for d in resolved_disputes if d.resolved_at and d.created_at
    ]
    avg_dispute_resolution = round(sum(dispute_resolution_seconds) / len(dispute_resolution_seconds), 1) if dispute_resolution_seconds else None
    dispute_backlog = _count(Dispute.query.filter(Dispute.status.in_(
        [DisputeStatus.OPEN, DisputeStatus.INVESTIGATING, DisputeStatus.ACTION_REQUIRED]
    )))

    return {
        "date_from": start.isoformat(), "date_to": end.isoformat(),
        "tickets": {
            "total": total_tickets, "by_status": tickets_by_status, "by_category": tickets_by_category,
            "backlog": backlog, "avg_resolution_seconds": avg_resolution,
        },
        "disputes": {
            "total": total_disputes, "by_status": disputes_by_status, "by_category": disputes_by_category,
            "backlog": dispute_backlog, "avg_resolution_seconds": avg_dispute_resolution,
        },
    }


# --- Overview --------------------------------------------------------------

def overview(date_from: str | None = None, date_to: str | None = None) -> dict:
    return {
        "orders": orders_metrics(date_from, date_to),
        "finance": finance_metrics(date_from, date_to),
        "delivery": delivery_metrics(date_from, date_to),
        "customers": customer_metrics(date_from, date_to),
        "support_disputes": support_dispute_metrics(date_from, date_to),
    }
