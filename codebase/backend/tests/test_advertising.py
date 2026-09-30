from decimal import Decimal

from tests.growth_fixtures import GrowthFixtures


class TestAdCampaignLifecycle(GrowthFixtures):
    def test_campaign_requires_admin_approval_before_it_can_serve_events(
        self, client, vendor, customer, admin, login_as
    ):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, _zone, _product = self.setup_branch_with_zone(client, vheaders)
        campaign, resp = self.create_campaign(client, vheaders, branch)
        assert resp.status_code == 201
        assert campaign["status"] == "PENDING_REVIEW"

        blocked = client.post(
            f"/api/v1/ads/campaigns/{campaign['id']}/events", headers=cheaders, json={"event_type": "IMPRESSION"}
        )
        assert blocked.status_code == 422
        assert blocked.get_json()["error"]["code"] == "AD_CAMPAIGN_NOT_ACTIVE"

        approve = client.post(f"/api/v1/admin/ad-campaigns/{campaign['id']}/approve", headers=aheaders)
        assert approve.status_code == 200
        assert approve.get_json()["data"]["campaign"]["status"] == "ACTIVE"

        allowed = client.post(
            f"/api/v1/ads/campaigns/{campaign['id']}/events", headers=cheaders, json={"event_type": "IMPRESSION"}
        )
        assert allowed.status_code == 201

    def test_admin_can_reject_a_pending_campaign_with_a_reason(self, client, vendor, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, _zone, _product = self.setup_branch_with_zone(client, vheaders)
        campaign, _resp = self.create_campaign(client, vheaders, branch)

        resp = client.post(
            f"/api/v1/admin/ad-campaigns/{campaign['id']}/reject", headers=aheaders, json={"reason": "Not suitable"}
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["campaign"]["status"] == "REJECTED"
        assert resp.get_json()["data"]["campaign"]["rejection_reason"] == "Not suitable"

    def test_a_click_on_a_cpc_campaign_bills_the_bid_amount_and_debits_the_vendor(
        self, client, vendor, customer, rider, admin, login_as
    ):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        # Ad spend is capped at the vendor's available balance (see
        # app/advertising/service.py) - fund it first via a normal
        # delivered-and-settled order, the same way Phase 5's settlement
        # tests establish a starting vendor balance.
        self.deliver_full_order(client, vheaders, cheaders, rheaders, aheaders, branch, zone, product)
        starting_balance = Decimal(
            client.get("/api/v1/vendor/financial-summary", headers=vheaders).get_json()["data"]["account"]["payable_balance"]
        )
        assert starting_balance > 0

        campaign, _resp = self.create_campaign(client, vheaders, branch, bid_amount="0.7500", total_budget="10.00")
        client.post(f"/api/v1/admin/ad-campaigns/{campaign['id']}/approve", headers=aheaders)

        # An impression on a CPC campaign is tracked but not billed.
        client.post(
            f"/api/v1/ads/campaigns/{campaign['id']}/events", headers=cheaders,
            json={"event_type": "IMPRESSION", "event_reference": "imp-1"},
        )
        click = client.post(
            f"/api/v1/ads/campaigns/{campaign['id']}/events", headers=cheaders,
            json={"event_type": "CLICK", "event_reference": "click-1"},
        ).get_json()["data"]["event"]
        assert Decimal(click["billed_amount"]) == Decimal("0.7500")

        summary = client.get("/api/v1/vendor/financial-summary", headers=vheaders).get_json()["data"]
        assert Decimal(summary["account"]["payable_balance"]) == starting_balance - Decimal("0.75")

        campaign_detail = client.get(f"/api/v1/vendor/ad-campaigns/{campaign['id']}", headers=vheaders).get_json()["data"]["campaign"]
        assert Decimal(campaign_detail["spent_total"]) == Decimal("0.75")
        assert campaign_detail["performance"]["clicks"] == 1
        assert campaign_detail["performance"]["impressions"] == 1

    def test_ad_spend_never_takes_a_vendors_balance_negative(self, client, vendor, customer, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, _zone, _product = self.setup_branch_with_zone(client, vheaders)
        # No prior earnings - vendor's payable balance starts at 0.
        campaign, _resp = self.create_campaign(client, vheaders, branch, bid_amount="5.0000", total_budget="50.00")
        client.post(f"/api/v1/admin/ad-campaigns/{campaign['id']}/approve", headers=aheaders)

        click = client.post(
            f"/api/v1/ads/campaigns/{campaign['id']}/events", headers=cheaders,
            json={"event_type": "CLICK", "event_reference": "c1"},
        ).get_json()["data"]["event"]
        assert Decimal(click["billed_amount"]) == Decimal("0")

        summary = client.get("/api/v1/vendor/financial-summary", headers=vheaders).get_json()["data"]
        assert Decimal(summary["account"]["payable_balance"]) == Decimal("0")

    def test_repeating_the_same_event_reference_never_double_bills(
        self, client, vendor, customer, rider, admin, login_as
    ):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        self.deliver_full_order(client, vheaders, cheaders, rheaders, aheaders, branch, zone, product)

        campaign, _resp = self.create_campaign(client, vheaders, branch, bid_amount="1.0000", total_budget="10.00")
        client.post(f"/api/v1/admin/ad-campaigns/{campaign['id']}/approve", headers=aheaders)

        for _ in range(3):
            client.post(
                f"/api/v1/ads/campaigns/{campaign['id']}/events", headers=cheaders,
                json={"event_type": "CLICK", "event_reference": "dup-click"},
            )

        campaign_detail = client.get(f"/api/v1/vendor/ad-campaigns/{campaign['id']}", headers=vheaders).get_json()["data"]["campaign"]
        assert Decimal(campaign_detail["spent_total"]) == Decimal("1.00")

    def test_campaign_moves_to_budget_exhausted_once_spend_reaches_the_cap(
        self, client, vendor, customer, rider, admin, login_as
    ):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        self.deliver_full_order(client, vheaders, cheaders, rheaders, aheaders, branch, zone, product)

        campaign, _resp = self.create_campaign(client, vheaders, branch, bid_amount="1.0000", total_budget="1.00")
        client.post(f"/api/v1/admin/ad-campaigns/{campaign['id']}/approve", headers=aheaders)

        client.post(
            f"/api/v1/ads/campaigns/{campaign['id']}/events", headers=cheaders,
            json={"event_type": "CLICK", "event_reference": "c1"},
        )
        campaign_detail = client.get(f"/api/v1/vendor/ad-campaigns/{campaign['id']}", headers=vheaders).get_json()["data"]["campaign"]
        assert campaign_detail["status"] == "BUDGET_EXHAUSTED"

        blocked = client.post(
            f"/api/v1/ads/campaigns/{campaign['id']}/events", headers=cheaders,
            json={"event_type": "CLICK", "event_reference": "c2"},
        )
        assert blocked.status_code == 422

    def test_vendor_cannot_target_another_vendors_branch(self, client, vendor, vendor2, login_as):
        vheaders = login_as(client, "vendor@example.com")
        vheaders2 = login_as(client, "vendor2@example.com")
        branch, _zone, _product = self.setup_branch_with_zone(client, vheaders)

        resp = client.post(
            "/api/v1/vendor/ad-campaigns", headers=vheaders2,
            json={
                "name": "Sneaky ad", "target_type": "BRANCH", "target_id": branch["id"],
                "bid_amount": "0.50", "total_budget": "5.00",
            },
        )
        assert resp.status_code == 403

    def test_vendor_can_pause_and_resume_an_active_campaign(self, client, vendor, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, _zone, _product = self.setup_branch_with_zone(client, vheaders)
        campaign, _resp = self.create_campaign(client, vheaders, branch)
        client.post(f"/api/v1/admin/ad-campaigns/{campaign['id']}/approve", headers=aheaders)

        paused = client.post(f"/api/v1/vendor/ad-campaigns/{campaign['id']}/pause", headers=vheaders)
        assert paused.get_json()["data"]["campaign"]["status"] == "PAUSED"

        resumed = client.post(f"/api/v1/vendor/ad-campaigns/{campaign['id']}/resume", headers=vheaders)
        assert resumed.get_json()["data"]["campaign"]["status"] == "ACTIVE"
