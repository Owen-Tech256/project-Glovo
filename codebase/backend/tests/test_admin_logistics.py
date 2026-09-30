from tests.logistics_fixtures import LogisticsFixtures, BRANCH_LAT, BRANCH_LNG


class TestAdminDeliveryMonitoring(LogisticsFixtures):
    def test_admin_lists_deliveries(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        self.onboard_available_rider(client, aheaders, rheaders, zone["id"])
        self.place_order_to_ready(client, vheaders, cheaders, branch, product)

        resp = client.get("/api/v1/admin/deliveries", headers=aheaders)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["pagination"]["total"] == 1

    def test_admin_filters_deliveries_by_status(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        self.onboard_available_rider(client, aheaders, rheaders, zone["id"])
        self.place_order_to_ready(client, vheaders, cheaders, branch, product)

        resp = client.get("/api/v1/admin/deliveries?status=DELIVERED", headers=aheaders)
        assert resp.get_json()["data"]["pagination"]["total"] == 0

    def test_admin_gets_delivery_detail_with_history(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        self.onboard_available_rider(client, aheaders, rheaders, zone["id"])
        self.place_order_to_ready(client, vheaders, cheaders, branch, product)

        delivery_id = client.get("/api/v1/admin/deliveries", headers=aheaders).get_json()["data"]["deliveries"][0]["id"]
        resp = client.get(f"/api/v1/admin/deliveries/{delivery_id}", headers=aheaders)
        assert resp.status_code == 200
        assert len(resp.get_json()["data"]["delivery"]["status_history"]) >= 1

    def test_non_admin_cannot_list_deliveries(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        resp = client.get("/api/v1/admin/deliveries", headers=headers)
        assert resp.status_code == 403


class TestAdminReassignment(LogisticsFixtures):
    def test_reassign_frees_previous_rider_and_finds_new_one(
        self, client, vendor, customer, rider, rider2, admin, login_as
    ):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        r1headers = login_as(client, "rider@example.com")
        r2headers = login_as(client, "rider2@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        self.onboard_available_rider(client, aheaders, r1headers, zone["id"])
        self.place_order_to_ready(client, vheaders, cheaders, branch, product)

        offer = client.get("/api/v1/rider/delivery-offers", headers=r1headers).get_json()["data"]["offers"][0]
        delivery = client.post(
            f"/api/v1/rider/delivery-offers/{offer['id']}/accept", headers=r1headers
        ).get_json()["data"]["delivery"]
        assert delivery["status"] == "ASSIGNED"

        # rider2 comes online only now, after rider1 was already assigned.
        self.onboard_available_rider(client, aheaders, r2headers, zone["id"])

        resp = client.post(
            f"/api/v1/admin/deliveries/{delivery['id']}/reassign", headers=aheaders,
            json={"reason": "Rider unresponsive"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["delivery"]["status"] in ("SEARCHING", "OFFERED")

        me1 = client.get("/api/v1/rider/me", headers=r1headers).get_json()["data"]["rider"]
        assert me1["operational_status"] == "AVAILABLE"

        offers2 = client.get("/api/v1/rider/delivery-offers", headers=r2headers).get_json()["data"]["offers"]
        assert len(offers2) == 1

        # rider1 is not re-offered the delivery they were just pulled from.
        offers1 = client.get("/api/v1/rider/delivery-offers", headers=r1headers).get_json()["data"]["offers"]
        assert offers1 == []

    def test_cannot_reassign_delivered_delivery(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        self.onboard_available_rider(client, aheaders, rheaders, zone["id"])
        self.place_order_to_ready(client, vheaders, cheaders, branch, product)
        offer = client.get("/api/v1/rider/delivery-offers", headers=rheaders).get_json()["data"]["offers"][0]
        delivery = client.post(
            f"/api/v1/rider/delivery-offers/{offer['id']}/accept", headers=rheaders
        ).get_json()["data"]["delivery"]
        client.post(f"/api/v1/deliveries/{delivery['id']}/pickup", headers=rheaders)
        client.post(f"/api/v1/deliveries/{delivery['id']}/start", headers=rheaders)
        client.post(f"/api/v1/deliveries/{delivery['id']}/complete", headers=rheaders)

        resp = client.post(f"/api/v1/admin/deliveries/{delivery['id']}/reassign", headers=aheaders, json={})
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "NOT_REASSIGNABLE"

    def test_reassign_retries_dispatch_for_stuck_searching_delivery(
        self, client, vendor, customer, rider, admin, login_as
    ):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        # No rider online at all when the order goes READY.
        self.place_order_to_ready(client, vheaders, cheaders, branch, product)

        delivery_id = client.get("/api/v1/admin/deliveries", headers=aheaders).get_json()["data"]["deliveries"][0]["id"]
        assert client.get(f"/api/v1/admin/deliveries/{delivery_id}", headers=aheaders).get_json()["data"]["delivery"]["status"] == "SEARCHING"

        # Rider comes online after the fact.
        self.onboard_available_rider(client, aheaders, rheaders, zone["id"])

        resp = client.post(f"/api/v1/admin/deliveries/{delivery_id}/reassign", headers=aheaders, json={})
        assert resp.status_code == 200

        offers = client.get("/api/v1/rider/delivery-offers", headers=rheaders).get_json()["data"]["offers"]
        assert len(offers) == 1

    def test_non_admin_cannot_reassign(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        self.onboard_available_rider(client, aheaders, rheaders, zone["id"])
        self.place_order_to_ready(client, vheaders, cheaders, branch, product)
        delivery_id = client.get("/api/v1/admin/deliveries", headers=aheaders).get_json()["data"]["deliveries"][0]["id"]

        resp = client.post(f"/api/v1/admin/deliveries/{delivery_id}/reassign", headers=rheaders, json={})
        assert resp.status_code == 403


class TestDispatchHealth(LogisticsFixtures):
    """Phase 9: aggregate status visibility into the automated dispatch
    engine - see app/logistics/admin_service.py:get_dispatch_health."""

    def test_reports_zero_counts_with_no_active_deliveries(self, client, admin, login_as):
        aheaders = login_as(client, "admin@example.com")
        resp = client.get("/api/v1/admin/logistics/dispatch-health", headers=aheaders)
        assert resp.status_code == 200
        health = resp.get_json()["data"]["dispatch_health"]
        assert health == {
            "searching_count": 0,
            "offered_count": 0,
            "stuck_count": 0,
            "stuck_threshold_seconds": 180,
            "stuck_deliveries": [],
        }

    def test_counts_a_delivery_still_searching_for_a_rider(self, client, vendor, customer, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, _zone, product = self.setup_branch_with_zone(client, vheaders)
        # No rider ever onboarded/available, so dispatch finds zero
        # candidates and the delivery is left SEARCHING.
        self.place_order_to_ready(client, vheaders, cheaders, branch, product)

        health = client.get(
            "/api/v1/admin/logistics/dispatch-health", headers=aheaders
        ).get_json()["data"]["dispatch_health"]
        assert health["searching_count"] == 1
        assert health["offered_count"] == 0
        # Freshly created - not old enough to count as "stuck" yet.
        assert health["stuck_count"] == 0

    def test_counts_an_offered_delivery(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        self.onboard_available_rider(client, aheaders, rheaders, zone["id"])
        self.place_order_to_ready(client, vheaders, cheaders, branch, product)

        health = client.get(
            "/api/v1/admin/logistics/dispatch-health", headers=aheaders
        ).get_json()["data"]["dispatch_health"]
        assert health["searching_count"] == 0
        assert health["offered_count"] == 1
        assert health["stuck_count"] == 0

    def test_flags_an_old_searching_delivery_as_stuck(self, client, vendor, customer, admin, login_as, db):
        from datetime import timedelta

        from app.logistics.helpers import utcnow
        from app.models.delivery import Delivery

        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, _zone, product = self.setup_branch_with_zone(client, vheaders)
        self.place_order_to_ready(client, vheaders, cheaders, branch, product)

        delivery = Delivery.query.first()
        delivery.created_at = utcnow() - timedelta(seconds=181)
        db.session.commit()

        health = client.get(
            "/api/v1/admin/logistics/dispatch-health", headers=aheaders
        ).get_json()["data"]["dispatch_health"]
        assert health["stuck_count"] == 1
        assert health["stuck_deliveries"][0]["id"] == delivery.public_id

    def test_non_admin_cannot_view_dispatch_health(self, client, vendor, login_as):
        vheaders = login_as(client, "vendor@example.com")
        resp = client.get("/api/v1/admin/logistics/dispatch-health", headers=vheaders)
        assert resp.status_code == 403
