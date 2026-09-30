from tests.logistics_fixtures import LogisticsFixtures


class _AssignedDeliveryFixtures(LogisticsFixtures):
    def _setup_assigned_delivery(self, client, vheaders, cheaders, rheaders, aheaders):
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        self.onboard_available_rider(client, aheaders, rheaders, zone["id"])
        self.place_order_to_ready(client, vheaders, cheaders, branch, product)
        offer = client.get("/api/v1/rider/delivery-offers", headers=rheaders).get_json()["data"]["offers"][0]
        delivery = client.post(
            f"/api/v1/rider/delivery-offers/{offer['id']}/accept", headers=rheaders
        ).get_json()["data"]["delivery"]
        order = client.get("/api/v1/orders", headers=cheaders).get_json()["data"]["orders"][0]
        return order, delivery


class TestTrackingVisibility(_AssignedDeliveryFixtures):
    def test_customer_sees_own_delivery(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        order, delivery = self._setup_assigned_delivery(client, vheaders, cheaders, rheaders, aheaders)

        resp = client.get(f"/api/v1/deliveries/{delivery['id']}/tracking", headers=cheaders)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["delivery"]["status"] == "ASSIGNED"

    def test_customer_cannot_see_another_customers_delivery(
        self, client, vendor, customer, customer2, rider, admin, login_as
    ):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        _order, delivery = self._setup_assigned_delivery(client, vheaders, cheaders, rheaders, aheaders)

        c2headers = login_as(client, "customer2@example.com")
        resp = client.get(f"/api/v1/deliveries/{delivery['id']}/tracking", headers=c2headers)
        assert resp.status_code == 404

    def test_vendor_sees_own_branch_delivery(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        order, delivery = self._setup_assigned_delivery(client, vheaders, cheaders, rheaders, aheaders)

        resp = client.get(f"/api/v1/vendor/orders/{order['id']}/delivery", headers=vheaders)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["delivery"]["id"] == delivery["id"]

    def test_other_vendor_cannot_see_delivery(self, client, vendor, vendor2, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        order, _delivery = self._setup_assigned_delivery(client, vheaders, cheaders, rheaders, aheaders)

        v2headers = login_as(client, "vendor2@example.com")
        resp = client.get(f"/api/v1/vendor/orders/{order['id']}/delivery", headers=v2headers)
        assert resp.status_code == 404

    def test_assigned_rider_sees_delivery(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        _order, delivery = self._setup_assigned_delivery(client, vheaders, cheaders, rheaders, aheaders)

        resp = client.get(f"/api/v1/deliveries/{delivery['id']}/tracking", headers=rheaders)
        assert resp.status_code == 200

    def test_unrelated_rider_cannot_see_delivery(self, client, vendor, customer, rider, rider2, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        _order, delivery = self._setup_assigned_delivery(client, vheaders, cheaders, rheaders, aheaders)

        r2headers = login_as(client, "rider2@example.com")
        resp = client.get(f"/api/v1/deliveries/{delivery['id']}/tracking", headers=r2headers)
        assert resp.status_code == 404

    def test_admin_sees_any_delivery(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        _order, delivery = self._setup_assigned_delivery(client, vheaders, cheaders, rheaders, aheaders)

        resp = client.get(f"/api/v1/deliveries/{delivery['id']}/tracking", headers=aheaders)
        assert resp.status_code == 200


class TestLocationExposure(_AssignedDeliveryFixtures):
    def test_no_rider_location_before_assignment(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        self.place_order_to_ready(client, vheaders, cheaders, branch, product)

        order = client.get("/api/v1/orders", headers=cheaders).get_json()["data"]["orders"][0]
        resp = client.get(f"/api/v1/orders/{order['id']}/delivery", headers=cheaders)
        assert resp.get_json()["data"]["rider_location"] is None

    def test_rider_location_visible_once_assigned(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        _order, delivery = self._setup_assigned_delivery(client, vheaders, cheaders, rheaders, aheaders)

        resp = client.get(f"/api/v1/deliveries/{delivery['id']}/tracking", headers=cheaders)
        location = resp.get_json()["data"]["rider_location"]
        assert location is not None
        assert location["is_stale"] is False

    def test_rider_location_hidden_after_delivered(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        _order, delivery = self._setup_assigned_delivery(client, vheaders, cheaders, rheaders, aheaders)
        client.post(f"/api/v1/deliveries/{delivery['id']}/pickup", headers=rheaders)
        client.post(f"/api/v1/deliveries/{delivery['id']}/start", headers=rheaders)
        client.post(f"/api/v1/deliveries/{delivery['id']}/complete", headers=rheaders)

        resp = client.get(f"/api/v1/deliveries/{delivery['id']}/tracking", headers=cheaders)
        assert resp.get_json()["data"]["rider_location"] is None
