from tests.support_fixtures import SupportFixtures


class _F(SupportFixtures):
    def _delivered_order(self, client, vheaders, cheaders, rheaders, aheaders):
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        return self.deliver_full_order(client, vheaders, cheaders, rheaders, aheaders, branch, zone, product)


class TestAnalyticsAccess(_F):
    def test_customer_cannot_access_analytics(self, client, customer, login_as):
        headers = login_as(client, "customer@example.com")
        resp = client.get("/api/v1/analytics/overview", headers=headers)
        assert resp.status_code == 403

    def test_moderator_cannot_access_analytics(self, client, moderator, login_as):
        headers = login_as(client, "moderator@example.com")
        resp = client.get("/api/v1/analytics/overview", headers=headers)
        assert resp.status_code == 403

    def test_analyst_can_access_analytics(self, client, analyst, login_as):
        headers = login_as(client, "analyst@example.com")
        resp = client.get("/api/v1/analytics/overview", headers=headers)
        assert resp.status_code == 200

    def test_finance_admin_can_access_finance_but_ops_cannot(self, client, finance_admin, operations_admin, login_as):
        fheaders = login_as(client, "financeadmin@example.com")
        oheaders = login_as(client, "ops@example.com")
        assert client.get("/api/v1/analytics/finance", headers=fheaders).status_code == 200
        assert client.get("/api/v1/analytics/finance", headers=oheaders).status_code == 403


class TestAnalyticsNumbers(_F):
    def test_orders_metrics_reflect_a_delivered_order(self, client, vendor, customer, rider, admin, analyst, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        anheaders = login_as(client, "analyst@example.com")
        order, _delivery = self._delivered_order(client, vheaders, cheaders, rheaders, aheaders)

        resp = client.get("/api/v1/analytics/orders", headers=anheaders)
        data = resp.get_json()["data"]
        assert data["total_orders"] >= 1
        assert data["delivered_orders"] >= 1
        assert data["orders_by_status"]["DELIVERED"] >= 1

    def test_finance_metrics_reflect_successful_payment(self, client, vendor, customer, rider, admin, analyst, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        anheaders = login_as(client, "analyst@example.com")
        self._delivered_order(client, vheaders, cheaders, rheaders, aheaders)

        resp = client.get("/api/v1/analytics/finance", headers=anheaders)
        data = resp.get_json()["data"]
        assert data["successful_payments"] >= 1
        assert float(data["gross_revenue"]) > 0

    def test_vendor_metrics_returns_the_vendor(self, client, vendor, customer, rider, admin, analyst, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        anheaders = login_as(client, "analyst@example.com")
        self._delivered_order(client, vheaders, cheaders, rheaders, aheaders)

        resp = client.get("/api/v1/analytics/vendors", headers=anheaders)
        vendors = resp.get_json()["data"]["vendors"]
        assert len(vendors) == 1
        assert vendors[0]["order_count"] == 1

    def test_rider_metrics_returns_the_rider(self, client, vendor, customer, rider, admin, analyst, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        anheaders = login_as(client, "analyst@example.com")
        self._delivered_order(client, vheaders, cheaders, rheaders, aheaders)

        resp = client.get("/api/v1/analytics/riders", headers=anheaders)
        riders = resp.get_json()["data"]["riders"]
        assert len(riders) == 1
        assert riders[0]["completed_deliveries"] == 1

    def test_support_disputes_metrics_reflect_a_ticket(self, client, customer, analyst, login_as):
        cheaders = login_as(client, "customer@example.com")
        anheaders = login_as(client, "analyst@example.com")
        self.open_ticket(client, cheaders, subject="Analytics test ticket")

        resp = client.get("/api/v1/analytics/support-disputes", headers=anheaders)
        data = resp.get_json()["data"]
        assert data["tickets"]["total"] >= 1
        assert data["tickets"]["backlog"] >= 1
