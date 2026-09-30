from tests.payments_fixtures import PaymentsFixtures


class TestAdminFinanceAuthorization(PaymentsFixtures):
    def test_non_admin_cannot_list_payments(self, client, customer, login_as):
        cheaders = login_as(client, "customer@example.com")
        resp = client.get("/api/v1/admin/payments", headers=cheaders)
        assert resp.status_code == 403

    def test_non_admin_cannot_list_refunds(self, client, customer, login_as):
        cheaders = login_as(client, "customer@example.com")
        resp = client.get("/api/v1/admin/refunds", headers=cheaders)
        assert resp.status_code == 403

    def test_non_admin_cannot_list_payouts(self, client, customer, login_as):
        cheaders = login_as(client, "customer@example.com")
        resp = client.get("/api/v1/admin/payouts", headers=cheaders)
        assert resp.status_code == 403

    def test_non_admin_cannot_view_reconciliation(self, client, customer, login_as):
        cheaders = login_as(client, "customer@example.com")
        resp = client.get("/api/v1/admin/reconciliation/summary", headers=cheaders)
        assert resp.status_code == 403

    def test_unauthenticated_cannot_access_any_admin_finance_route(self, client):
        assert client.get("/api/v1/admin/payments").status_code == 401
        assert client.get("/api/v1/admin/commission-rules").status_code == 401


class TestAdminFinanceListingsAndFiltering(PaymentsFixtures):
    def test_admin_can_list_and_filter_payments_by_status(self, client, vendor, customer, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, _zone, product = self.setup_branch_with_zone(client, vheaders)
        self.place_order(client, vheaders, cheaders, branch, product)  # auto-pays via place_order

        resp = client.get("/api/v1/admin/payments?status=SUCCEEDED", headers=aheaders)
        assert resp.status_code == 200
        payments = resp.get_json()["data"]["payments"]
        assert len(payments) == 1
        assert payments[0]["status"] == "SUCCEEDED"

    def test_admin_commission_rule_listing_includes_bootstrap_default(
        self, client, vendor, customer, rider, admin, login_as
    ):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        # Triggers the lazy bootstrap default commission rule.
        self.deliver_full_order(client, vheaders, cheaders, rheaders, aheaders, branch, zone, product)

        resp = client.get("/api/v1/admin/commission-rules", headers=aheaders)
        assert resp.status_code == 200
        rules = resp.get_json()["data"]["commission_rules"]
        assert len(rules) == 1
        assert rules[0]["percentage_rate"] == "0.1500"


class TestReconciliationAfterFullLifecycle(PaymentsFixtures):
    def test_ledger_stays_balanced_through_payment_settlement_and_payout(
        self, client, vendor, customer, rider, admin, login_as
    ):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        self.deliver_full_order(client, vheaders, cheaders, rheaders, aheaders, branch, zone, product)

        # Vendor cashes out.
        client.post("/api/v1/vendor/payouts", headers=vheaders, json={"destination_reference": "Bank ****1234"})
        # Rider gets a manual adjustment too.
        rider_id = client.get("/api/v1/rider/me", headers=rheaders).get_json()["data"]["rider"]["id"]
        client.post(
            "/api/v1/admin/wallet-adjustments", headers=aheaders,
            json={"rider_id": rider_id, "amount": "5.00", "reason": "bonus"},
        )

        resp = client.get("/api/v1/admin/reconciliation/summary", headers=aheaders)
        summary = resp.get_json()["data"]
        assert summary["balanced"] is True
        assert summary["total_debits"] == summary["total_credits"]
