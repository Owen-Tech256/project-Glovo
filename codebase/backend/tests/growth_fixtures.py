"""
Shared setup helpers for the Phase 6 growth & engagement test suite,
building on top of PaymentsFixtures (Phase 5) the same way Phase 5's own
tests built on LogisticsFixtures (Phase 4).
"""
from tests.payments_fixtures import PaymentsFixtures


class GrowthFixtures(PaymentsFixtures):
    def create_promotion(self, client, vheaders, **overrides):
        payload = {
            "name": "10 off",
            "type": "PERCENTAGE",
            "value": "10",
            "scope_type": "ORDER",
        }
        payload.update(overrides)
        resp = client.post("/api/v1/vendor/promotions", headers=vheaders, json=payload)
        body = resp.get_json()
        return body.get("data", {}).get("promotion"), resp

    def create_admin_promotion(self, client, aheaders, **overrides):
        payload = {
            "name": "Platform-wide",
            "type": "FIXED_AMOUNT",
            "value": "5.00",
            "scope_type": "ORDER",
        }
        payload.update(overrides)
        resp = client.post("/api/v1/admin/promotions", headers=aheaders, json=payload)
        body = resp.get_json()
        return body.get("data", {}).get("promotion"), resp

    def create_campaign(self, client, vheaders, branch, **overrides):
        payload = {
            "name": "Featured branch",
            "target_type": "BRANCH",
            "target_id": branch["id"],
            "pricing_model": "CPC",
            "bid_amount": "0.5000",
            "total_budget": "10.00",
        }
        payload.update(overrides)
        resp = client.post("/api/v1/vendor/ad-campaigns", headers=vheaders, json=payload)
        body = resp.get_json()
        return body.get("data", {}).get("campaign"), resp
