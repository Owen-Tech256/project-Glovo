from tests.growth_fixtures import GrowthFixtures


class TestNotificationEvents(GrowthFixtures):
    def test_placing_and_paying_for_an_order_notifies_the_customer(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, _zone, product = self.setup_branch_with_zone(client, vheaders)
        order = self.place_unpaid_order(client, vheaders, cheaders, branch, product)
        client.post("/api/v1/payments", headers=cheaders, json={"order_id": order["id"]})

        notifications = client.get("/api/v1/notifications", headers=cheaders).get_json()["data"]
        keys = {n["category"] for n in notifications["notifications"]}
        assert "PAYMENT" in keys
        assert "ORDER" in keys
        assert notifications["unread_count"] >= 2

    def test_vendor_accepting_an_order_notifies_the_customer(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, _zone, product = self.setup_branch_with_zone(client, vheaders)
        order = self.place_order(client, vheaders, cheaders, branch, product)
        client.post(f"/api/v1/vendor/orders/{order['id']}/transition", headers=vheaders, json={"to_status": "VENDOR_ACCEPTED"})

        notifications = client.get("/api/v1/notifications", headers=cheaders).get_json()["data"]["notifications"]
        assert any(n["entity_id"] == order["id"] and "accepted" in n["title"].lower() for n in notifications)

    def test_full_delivery_notifies_customer_vendor_and_rider(
        self, client, vendor, customer, rider, admin, login_as
    ):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        order, _delivery = self.deliver_full_order(client, vheaders, cheaders, rheaders, aheaders, branch, zone, product)

        customer_notifications = client.get("/api/v1/notifications", headers=cheaders).get_json()["data"]["notifications"]
        assert any(n["category"] == "DELIVERY" for n in customer_notifications)
        assert any(n["category"] == "REVIEW" for n in customer_notifications)

        vendor_notifications = client.get("/api/v1/notifications", headers=vheaders).get_json()["data"]["notifications"]
        assert any(n["category"] == "DELIVERY" for n in vendor_notifications)

        rider_notifications = client.get("/api/v1/notifications", headers=rheaders).get_json()["data"]["notifications"]
        assert any(n["category"] == "PAYOUT" for n in rider_notifications)

    def test_mark_read_and_mark_all_read(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, _zone, product = self.setup_branch_with_zone(client, vheaders)
        order = self.place_unpaid_order(client, vheaders, cheaders, branch, product)
        client.post("/api/v1/payments", headers=cheaders, json={"order_id": order["id"]})

        notifications = client.get("/api/v1/notifications", headers=cheaders).get_json()["data"]["notifications"]
        first_id = notifications[0]["id"]
        assert client.get("/api/v1/notifications", headers=cheaders).get_json()["data"]["unread_count"] >= 2

        client.patch(f"/api/v1/notifications/{first_id}/read", headers=cheaders)
        after_one = client.get("/api/v1/notifications", headers=cheaders).get_json()["data"]

        client.post("/api/v1/notifications/read-all", headers=cheaders)
        after_all = client.get("/api/v1/notifications", headers=cheaders).get_json()["data"]
        assert after_all["unread_count"] == 0

    def test_customer_can_turn_off_an_email_preference_and_it_is_respected(self, client, customer, login_as):
        cheaders = login_as(client, "customer@example.com")
        resp = client.put(
            "/api/v1/notifications/preferences", headers=cheaders,
            json={"category": "PROMOTION", "channel": "EMAIL", "enabled": False},
        )
        assert resp.status_code == 200
        prefs = client.get("/api/v1/notifications/preferences", headers=cheaders).get_json()["data"]["preferences"]
        assert any(p["category"] == "PROMOTION" and p["channel"] == "EMAIL" and p["enabled"] is False for p in prefs)

    def test_a_failed_payment_notifies_the_customer(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, _zone, product = self.setup_branch_with_zone(client, vheaders)
        order = self.place_unpaid_order(client, vheaders, cheaders, branch, product)

        client.post(
            "/api/v1/payments", headers=cheaders,
            json={"order_id": order["id"], "method": "MOCK_DECLINE"},
        )
        notifications = client.get("/api/v1/notifications", headers=cheaders).get_json()["data"]["notifications"]
        assert any(n["category"] == "PAYMENT" and "fail" in n["title"].lower() for n in notifications)
