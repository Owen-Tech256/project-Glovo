from decimal import Decimal, ROUND_HALF_UP

from tests.payments_fixtures import PaymentsFixtures


def _expected_commission(subtotal: Decimal, rate: Decimal, fixed: Decimal = Decimal("0")) -> Decimal:
    amount = (subtotal * rate) + fixed
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class TestSettlement(PaymentsFixtures):
    def test_settlement_splits_earnings_correctly_on_delivery(
        self, client, vendor, customer, rider, admin, login_as
    ):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")

        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        order, _delivery = self.deliver_full_order(client, vheaders, cheaders, rheaders, aheaders, branch, zone, product)
        assert order["status"] == "DELIVERED"

        subtotal = Decimal(order["subtotal"])
        fees = Decimal(order["fees"])
        total = Decimal(order["total"])
        assert total == subtotal + fees

        # Default bootstrap commission rate (see app/config.py).
        default_rate = Decimal("0.15")
        expected_commission = _expected_commission(subtotal, default_rate)
        expected_vendor_earnings = subtotal - expected_commission
        expected_rider_earnings = fees

        wallet = client.get("/api/v1/rider/wallet", headers=rheaders).get_json()["data"]["wallet"]
        assert Decimal(wallet["available_balance"]) == expected_rider_earnings

        vendor_summary = client.get("/api/v1/vendor/financial-summary", headers=vheaders).get_json()["data"]
        assert Decimal(vendor_summary["account"]["payable_balance"]) == expected_vendor_earnings

        # The three-way split always reconstitutes the full captured total.
        assert expected_vendor_earnings + expected_rider_earnings + expected_commission == total

        reconciliation = client.get("/api/v1/admin/reconciliation/summary", headers=aheaders).get_json()["data"]
        assert reconciliation["balanced"] is True

    def test_settlement_is_idempotent_if_triggered_twice(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")

        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        order, _delivery = self.deliver_full_order(client, vheaders, cheaders, rheaders, aheaders, branch, zone, product)

        wallet_before = client.get("/api/v1/rider/wallet", headers=rheaders).get_json()["data"]["wallet"]

        # Calling settle_order again directly must be a safe no-op (it is
        # already guarded by the ledger's own idempotency key) - simulate
        # this the same way a retried webhook/background job would.
        from app.payments import settlement_service
        from app.models.order import Order

        with client.application.app_context():
            db_order = Order.query.filter_by(public_id=order["id"]).first()
            settlement_service.settle_order(db_order)

        wallet_after = client.get("/api/v1/rider/wallet", headers=rheaders).get_json()["data"]["wallet"]
        assert wallet_before["available_balance"] == wallet_after["available_balance"]

    def test_admin_configured_commission_rule_is_applied_and_snapshotted(
        self, client, vendor, customer, rider, admin, login_as
    ):
        aheaders = login_as(client, "admin@example.com")
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")

        create_rule = client.post(
            "/api/v1/admin/commission-rules", headers=aheaders,
            json={"name": "Promo rate", "percentage_rate": "0.10", "fixed_amount": "0.00"},
        )
        assert create_rule.status_code == 201

        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        order, _delivery = self.deliver_full_order(client, vheaders, cheaders, rheaders, aheaders, branch, zone, product)

        subtotal = Decimal(order["subtotal"])
        expected_commission = _expected_commission(subtotal, Decimal("0.10"))
        expected_vendor_earnings = subtotal - expected_commission

        vendor_summary = client.get("/api/v1/vendor/financial-summary", headers=vheaders).get_json()["data"]
        assert Decimal(vendor_summary["account"]["payable_balance"]) == expected_vendor_earnings

    def test_editing_commission_rule_does_not_change_past_settlements(
        self, client, vendor, customer, rider, rider2, admin, login_as
    ):
        aheaders = login_as(client, "admin@example.com")
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")

        rule = client.post(
            "/api/v1/admin/commission-rules", headers=aheaders,
            json={"name": "Initial rate", "percentage_rate": "0.20"},
        ).get_json()["data"]["commission_rule"]

        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        order, _delivery = self.deliver_full_order(client, vheaders, cheaders, rheaders, aheaders, branch, zone, product)
        subtotal = Decimal(order["subtotal"])
        first_vendor_earnings = subtotal - _expected_commission(subtotal, Decimal("0.20"))

        vendor_summary = client.get("/api/v1/vendor/financial-summary", headers=vheaders).get_json()["data"]
        assert Decimal(vendor_summary["account"]["payable_balance"]) == first_vendor_earnings

        # Now change the rate going forward.
        client.patch(
            f"/api/v1/admin/commission-rules/{rule['id']}", headers=aheaders, json={"percentage_rate": "0.50"}
        )

        # The already-settled order's vendor payable balance is untouched.
        vendor_summary_after = client.get("/api/v1/vendor/financial-summary", headers=vheaders).get_json()["data"]
        assert Decimal(vendor_summary_after["account"]["payable_balance"]) == first_vendor_earnings

    def test_non_admin_cannot_manage_commission_rules(self, client, vendor, login_as):
        vheaders = login_as(client, "vendor@example.com")
        resp = client.post(
            "/api/v1/admin/commission-rules", headers=vheaders, json={"name": "x", "percentage_rate": "0.1"}
        )
        assert resp.status_code == 403
