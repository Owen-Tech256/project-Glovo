class _AdminOrderFixtures:
    def _place_order(self, client, vheaders, cheaders):
        branch = client.post(
            "/api/v1/vendors/me/branches",
            headers=vheaders,
            json={"name": "Branch", "address": "1 Main St", "latitude": 40.7128, "longitude": -74.0060},
        ).get_json()["data"]["branch"]
        client.post(
            f"/api/v1/vendors/me/branches/{branch['id']}/zones",
            headers=vheaders,
            json={"name": "zone", "center_latitude": 40.7128, "center_longitude": -74.0060, "radius_meters": 5000},
        )
        category = client.post(
            "/api/v1/vendors/me/categories", headers=vheaders, json={"name": "Pizzas"}
        ).get_json()["data"]["category"]
        product = client.post(
            "/api/v1/vendors/me/products",
            headers=vheaders,
            json={"category_id": category["id"], "name": "Margherita", "price": "9.99"},
        ).get_json()["data"]["product"]
        client.put(
            f"/api/v1/vendors/me/branches/{branch['id']}/products/{product['id']}",
            headers=vheaders,
            json={"availability_status": "AVAILABLE"},
        )
        address = client.post(
            "/api/v1/addresses", headers=cheaders,
            json={
                "label": "Home", "recipient_name": "Cara Customer", "phone": "+12025550123",
                "address_line1": "123 Main St", "city": "New York", "country": "USA",
                "latitude": 40.7128, "longitude": -74.0060,
            },
        ).get_json()["data"]["address"]
        client.post(
            "/api/v1/cart/items", headers=cheaders,
            json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 1},
        )
        order = client.post(
            "/api/v1/orders", headers=cheaders, json={"branch_id": branch["id"], "address_id": address["id"]}
        ).get_json()["data"]["order"]
        return branch, order


class TestAdminOrderOversight(_AdminOrderFixtures):
    def test_admin_can_list_all_orders(self, client, vendor, customer, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        self._place_order(client, vheaders, cheaders)

        aheaders = login_as(client, "admin@example.com")
        resp = client.get("/api/v1/admin/orders", headers=aheaders)
        assert resp.status_code == 200
        assert len(resp.get_json()["data"]["orders"]) == 1

    def test_admin_can_get_order_detail(self, client, vendor, customer, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        _branch, order = self._place_order(client, vheaders, cheaders)

        aheaders = login_as(client, "admin@example.com")
        resp = client.get(f"/api/v1/admin/orders/{order['id']}", headers=aheaders)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["order"]["id"] == order["id"]

    def test_admin_can_filter_orders_by_status(self, client, vendor, customer, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        _branch, order = self._place_order(client, vheaders, cheaders)
        client.post(f"/api/v1/orders/{order['id']}/cancel", headers=cheaders)

        aheaders = login_as(client, "admin@example.com")
        cancelled = client.get("/api/v1/admin/orders?status=CANCELLED", headers=aheaders).get_json()["data"]["orders"]
        confirmed = client.get("/api/v1/admin/orders?status=PAYMENT_CONFIRMED", headers=aheaders).get_json()["data"]["orders"]
        assert len(cancelled) == 1
        assert confirmed == []

    def test_non_admin_cannot_access_admin_order_oversight(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        self._place_order(client, vheaders, cheaders)

        resp = client.get("/api/v1/admin/orders", headers=cheaders)
        assert resp.status_code == 403

        resp2 = client.get("/api/v1/admin/orders", headers=vheaders)
        assert resp2.status_code == 403

    def test_admin_can_view_order_status_history(self, client, vendor, customer, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        _branch, order = self._place_order(client, vheaders, cheaders)
        # Phase 5: pay for the order so its history includes the
        # PAYMENT_CONFIRMED transition, matching this test's original intent.
        client.post("/api/v1/payments", headers=cheaders, json={"order_id": order["id"]})

        aheaders = login_as(client, "admin@example.com")
        resp = client.get(f"/api/v1/admin/orders/{order['id']}/status-history", headers=aheaders)
        assert resp.status_code == 200
        assert len(resp.get_json()["data"]["history"]) == 3
