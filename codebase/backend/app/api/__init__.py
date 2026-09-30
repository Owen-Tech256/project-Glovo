from app.auth.routes import auth_bp
from app.users.routes import users_bp
from app.api.admin_routes import admin_bp
from app.api.admin_catalog_routes import admin_catalog_bp
from app.api.admin_order_routes import admin_orders_bp
from app.api.health import health_bp
from app.vendors.routes import vendors_bp
from app.catalog.routes import catalog_bp
from app.addresses.routes import addresses_bp
from app.cart.routes import cart_bp
from app.orders.routes import checkout_bp, orders_bp
from app.orders.vendor_routes import vendor_orders_bp
from app.api.admin_logistics_routes import admin_logistics_bp
from app.logistics.rider_routes import rider_bp
from app.logistics.delivery_routes import deliveries_bp
from app.logistics.visibility_routes import order_delivery_bp, vendor_delivery_bp

from app.payments.routes import payments_bp
from app.payments.rider_routes import rider_wallet_bp
from app.payments.vendor_routes import vendor_finance_bp
from app.api.admin_finance_routes import admin_finance_bp

from app.promotions.routes import promotions_bp
from app.promotions.vendor_routes import vendor_promotions_bp
from app.advertising.routes import ads_bp
from app.advertising.vendor_routes import vendor_ads_bp
from app.reviews.routes import reviews_bp
from app.reviews.vendor_routes import my_reviews_bp
from app.notifications.routes import notifications_bp
from app.api.admin_growth_routes import admin_growth_bp

from app.support.routes import support_bp
from app.api.admin_support_routes import admin_support_bp
from app.disputes.routes import disputes_bp
from app.api.admin_dispute_routes import admin_disputes_bp
from app.api.admin_rbac_routes import admin_rbac_bp
from app.api.admin_audit_routes import admin_audit_bp
from app.analytics.routes import analytics_bp
from app.reports.routes import reports_bp


def register_blueprints(app):
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_catalog_bp)
    app.register_blueprint(admin_orders_bp)
    app.register_blueprint(vendors_bp)
    app.register_blueprint(catalog_bp)
    app.register_blueprint(addresses_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(checkout_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(vendor_orders_bp)
    app.register_blueprint(admin_logistics_bp)
    app.register_blueprint(rider_bp)
    app.register_blueprint(deliveries_bp)
    app.register_blueprint(order_delivery_bp)
    app.register_blueprint(vendor_delivery_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(rider_wallet_bp)
    app.register_blueprint(vendor_finance_bp)
    app.register_blueprint(admin_finance_bp)
    app.register_blueprint(promotions_bp)
    app.register_blueprint(vendor_promotions_bp)
    app.register_blueprint(ads_bp)
    app.register_blueprint(vendor_ads_bp)
    app.register_blueprint(reviews_bp)
    app.register_blueprint(my_reviews_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(admin_growth_bp)

    app.register_blueprint(support_bp)
    app.register_blueprint(admin_support_bp)
    app.register_blueprint(disputes_bp)
    app.register_blueprint(admin_disputes_bp)
    app.register_blueprint(admin_rbac_bp)
    app.register_blueprint(admin_audit_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(reports_bp)
