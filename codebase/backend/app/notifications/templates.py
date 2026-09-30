"""
Seed content for every notification event this phase fires (SRS 7's
"templated messages with variable substitution"). Only IN_APP templates are
seeded by default - EMAIL/SMS/PUSH templates for the same key are opt-in,
created by an admin via POST /admin/notification-templates when they
actually want that channel to fire for an event, rather than every event
blasting every channel out of the box (a deliberately conservative
default - see PHASE_6_NOTES.md).

Rendering is a plain str.format(**context) - simple substitution is all
SRS 7 asks for; a full templating engine (conditionals/loops) is out of
scope for this phase.
"""
from app.models.notification_template import NotificationChannel
from app.models.notification import NotificationCategory

# key -> (category, title_template, body_template)
DEFAULT_TEMPLATES: dict[str, tuple[str, str, str]] = {
    "order_confirmed": (
        NotificationCategory.ORDER.value,
        "Order confirmed",
        "Your order {order_number} has been confirmed and sent to the vendor.",
    ),
    "payment_succeeded": (
        NotificationCategory.PAYMENT.value,
        "Payment received",
        "We received your payment of {amount} {currency} for order {order_number}.",
    ),
    "payment_failed": (
        NotificationCategory.PAYMENT.value,
        "Payment failed",
        "Your payment for order {order_number} could not be processed. Please try again.",
    ),
    "order_accepted": (
        NotificationCategory.ORDER.value,
        "Order accepted",
        "{vendor_name} has accepted order {order_number} and started preparing it.",
    ),
    "rider_assigned": (
        NotificationCategory.DELIVERY.value,
        "Rider on the way",
        "A rider has been assigned to deliver order {order_number}.",
    ),
    "delivery_completed_customer": (
        NotificationCategory.DELIVERY.value,
        "Order delivered",
        "Order {order_number} has been delivered. Enjoy!",
    ),
    "delivery_completed_vendor": (
        NotificationCategory.DELIVERY.value,
        "Order delivered",
        "Order {order_number} was delivered to the customer.",
    ),
    "review_reminder": (
        NotificationCategory.REVIEW.value,
        "How was your order?",
        "Order {order_number} was just delivered - let us know how it went.",
    ),
    "refund_processed": (
        NotificationCategory.PAYMENT.value,
        "Refund processed",
        "A refund of {amount} {currency} for order {order_number} has been processed.",
    ),
    "wallet_earning_posted": (
        NotificationCategory.PAYOUT.value,
        "Earnings posted",
        "You earned {amount} {currency} for order {order_number}. It's now available in your wallet.",
    ),
    "payout_paid": (
        NotificationCategory.PAYOUT.value,
        "Payout sent",
        "Your payout of {amount} {currency} has been sent.",
    ),
    "payout_failed": (
        NotificationCategory.PAYOUT.value,
        "Payout failed",
        "Your payout of {amount} {currency} could not be processed. Please check your payout details.",
    ),
    "ad_campaign_approved": (
        NotificationCategory.ADVERTISING.value,
        "Campaign approved",
        "Your ad campaign \"{campaign_name}\" has been approved and is now live.",
    ),
    "ad_campaign_rejected": (
        NotificationCategory.ADVERTISING.value,
        "Campaign rejected",
        "Your ad campaign \"{campaign_name}\" was rejected: {reason}",
    ),
    "promotion_available": (
        NotificationCategory.PROMOTION.value,
        "New promotion available",
        "A new promotion, {promotion_name}, is now available.",
    ),
}


def get_or_create_template(key: str) -> "NotificationTemplate | None":
    """Lazily provisions the default IN_APP template for `key` on first
    use, the same get_or_create convention used throughout this codebase
    (get_or_create_vendor, get_or_create_account, ...). Returns None for
    an unrecognized key (a caller-side typo) rather than raising, so a
    single bad notify() call never breaks the business event around it."""
    from app.extensions import db
    from app.models.notification_template import NotificationTemplate, NotificationTemplateStatus

    existing = NotificationTemplate.query.filter_by(key=key, channel=NotificationChannel.IN_APP).first()
    if existing is not None:
        return existing

    seed = DEFAULT_TEMPLATES.get(key)
    if seed is None:
        return None
    category, title_template, body_template = seed
    template = NotificationTemplate(
        key=key, channel=NotificationChannel.IN_APP, category=category,
        title_template=title_template, body_template=body_template, status=NotificationTemplateStatus.ACTIVE,
    )
    db.session.add(template)
    try:
        db.session.flush()
    except Exception:
        db.session.rollback()
        template = NotificationTemplate.query.filter_by(key=key, channel=NotificationChannel.IN_APP).first()
        if template is None:
            raise
    return template
