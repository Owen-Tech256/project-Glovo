from tests.logistics_fixtures import LogisticsFixtures


class _ReadyDeliveryFixtures(LogisticsFixtures):
    def _setup_assigned_delivery(self, client, vheaders, cheaders, rheaders, aheaders):
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        self.onboard_available_rider(client, aheaders, rheaders, zone["id"])
        self.place_order_to_ready(client, vheaders, cheaders, branch, product)

        offer = client.get("/api/v1/rider/delivery-offers", headers=rheaders).get_json()["data"]["offers"][0]
        delivery = client.post(
            f"/api/v1/rider/delivery-offers/{offer['id']}/accept", headers=rheaders
        ).get_json()["data"]["delivery"]
        return delivery


class TestDeliveryWorkflow(_ReadyDeliveryFixtures):
    def test_full_pickup_to_delivered_workflow(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        delivery = self._setup_assigned_delivery(client, vheaders, cheaders, rheaders, aheaders)
        delivery_id = delivery["id"]

        pickup = client.post(f"/api/v1/deliveries/{delivery_id}/pickup", headers=rheaders)
        assert pickup.status_code == 200
        assert pickup.get_json()["data"]["delivery"]["status"] == "PICKED_UP"

        start = client.post(f"/api/v1/deliveries/{delivery_id}/start", headers=rheaders)
        assert start.get_json()["data"]["delivery"]["status"] == "DELIVERING"

        complete = client.post(f"/api/v1/deliveries/{delivery_id}/complete", headers=rheaders)
        assert complete.get_json()["data"]["delivery"]["status"] == "DELIVERED"

        order = client.get("/api/v1/orders", headers=cheaders).get_json()["data"]["orders"][0]
        assert order["status"] == "DELIVERED"

        me = client.get("/api/v1/rider/me", headers=rheaders).get_json()["data"]["rider"]
        assert me["operational_status"] == "AVAILABLE"

    def test_cannot_skip_pickup_and_go_straight_to_start(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        delivery = self._setup_assigned_delivery(client, vheaders, cheaders, rheaders, aheaders)

        resp = client.post(f"/api/v1/deliveries/{delivery['id']}/start", headers=rheaders)
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "INVALID_TRANSITION"

    def test_cannot_complete_before_start(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        delivery = self._setup_assigned_delivery(client, vheaders, cheaders, rheaders, aheaders)
        client.post(f"/api/v1/deliveries/{delivery['id']}/pickup", headers=rheaders)

        resp = client.post(f"/api/v1/deliveries/{delivery['id']}/complete", headers=rheaders)
        assert resp.status_code == 422

    def test_other_rider_cannot_act_on_someone_elses_delivery(
        self, client, vendor, customer, rider, rider2, admin, login_as
    ):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        r2headers = login_as(client, "rider2@example.com")
        aheaders = login_as(client, "admin@example.com")
        delivery = self._setup_assigned_delivery(client, vheaders, cheaders, rheaders, aheaders)

        resp = client.post(f"/api/v1/deliveries/{delivery['id']}/pickup", headers=r2headers)
        assert resp.status_code == 404

    def test_status_history_reflects_full_workflow(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        delivery = self._setup_assigned_delivery(client, vheaders, cheaders, rheaders, aheaders)
        client.post(f"/api/v1/deliveries/{delivery['id']}/pickup", headers=rheaders)

        history = client.get(
            f"/api/v1/deliveries/{delivery['id']}/status-history", headers=rheaders
        ).get_json()["data"]["status_history"]
        statuses = [h["to_status"] for h in history]
        assert "CREATED" in statuses
        assert "SEARCHING" in statuses
        assert "OFFERED" in statuses
        assert "ASSIGNED" in statuses
        assert "PICKED_UP" in statuses
