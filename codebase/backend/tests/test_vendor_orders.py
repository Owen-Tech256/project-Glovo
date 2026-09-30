class _VendorOrderFixtures:
    def _setup_branch_product(self, client, headers, price="9.99"):
        branch = client.post(
            "/api/v1/vendors/me/branches",
            headers=headers,
            json={"name": "Branch", "address": "1 Main St", "latitude": 40.7128, "longitude": -74.0060},
        ).get_json()["data"]["branch"]
        client.post(
            f"/api/v1/vendors/me/branches/{branch['id']}/zones",
            headers=headers,
            json={"name": "zone", "center_latitude": 40.7128, "center_longitude": -74.0060, "radius_meters": 5000},
        )
        category = client.post(
            "/api/v1/vendors/me/categories", headers=headers, json={"name": "Pizzas"}
        ).get_json()["data"]["category"]
        product = client.post(
            "/api/v1/vendors/me/products",
            headers=headers,
            json={"category_id": category["id"], "name": "Margherita", "price": price},
        ).get_json()["data"]["product"]
        client.put(
            f"/api/v1/vendors/me/branches/{branch['id']}/products/{product['id']}",
            headers=headers,
            json={"availability_status": "AVAILABLE"},
        )
        return branch, product

    def _make_address(self, client, headers):
        payload = {
            "label": "Home",
            "recipient_name": "Cara Customer",
            "phone": "+12025550123",
            "address_line1": "123 Main St",
            "city": "New York",
            "country": "USA",
            "latitude": 40.7128,
            "longitude": -74.0060,
        }
        return client.post("/api/v1/addresses", headers=headers, json=payload).get_json()["data"]["address"]

    def _place_order(self, client, vheaders, cheaders):
        branch, product = self._setup_branch_product(client, vheaders)
        address = self._make_address(client, cheaders)
        client.post(
            "/api/v1/cart/items", headers=cheaders,
            json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 1},
        )
        order = client.post(
            "/api/v1/orders", headers=cheaders, json={"branch_id": branch["id"], "address_id": address["id"]}
        ).get_json()["data"]["order"]
        # Phase 5: pay for the order so it reaches PAYMENT_CONFIRMED and the
        # vendor can act on it, same reasoning as logistics_fixtures.py.
        client.post("/api/v1/payments", headers=cheaders, json={"order_id": order["id"]})
        order = client.get(f"/api/v1/orders/{order['id']}", headers=cheaders).get_json()["data"]["order"]
        return branch, order


class TestVendorOrderQueue(_VendorOrderFixtures):
    def test_vendor_sees_orders_for_own_branch(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        self._place_order(client, vheaders, cheaders)

        resp = client.get("/api/v1/vendor/orders", headers=vheaders)
        assert resp.status_code == 200
        assert len(resp.get_json()["data"]["orders"]) == 1

    def test_vendor_cannot_see_another_vendors_orders(self, client, vendor, vendor2, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        self._place_order(client, vheaders, cheaders)

        v2headers = login_as(client, "vendor2@example.com")
        resp = client.get("/api/v1/vendor/orders", headers=v2headers)
        assert resp.get_json()["data"]["orders"] == []

    def test_vendor_cannot_view_another_vendors_order_detail(self, client, vendor, vendor2, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        _branch, order = self._place_order(client, vheaders, cheaders)

        v2headers = login_as(client, "vendor2@example.com")
        resp = client.get(f"/api/v1/vendor/orders/{order['id']}", headers=v2headers)
        assert resp.status_code == 404

    def test_customer_cannot_access_vendor_order_endpoints(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        _branch, order = self._place_order(client, vheaders, cheaders)

        resp = client.get(f"/api/v1/vendor/orders/{order['id']}", headers=cheaders)
        assert resp.status_code == 403


class TestVendorOrderTransitions(_VendorOrderFixtures):
    def test_vendor_can_accept_then_prepare_then_ready(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        _branch, order = self._place_order(client, vheaders, cheaders)
        url = f"/api/v1/vendor/orders/{order['id']}/transition"

        r1 = client.post(url, headers=vheaders, json={"to_status": "VENDOR_ACCEPTED"})
        assert r1.status_code == 200
        assert r1.get_json()["data"]["order"]["status"] == "VENDOR_ACCEPTED"

        r2 = client.post(url, headers=vheaders, json={"to_status": "PREPARING"})
        assert r2.get_json()["data"]["order"]["status"] == "PREPARING"

        r3 = client.post(url, headers=vheaders, json={"to_status": "READY"})
        assert r3.get_json()["data"]["order"]["status"] == "READY"

    def test_vendor_cannot_skip_states(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        _branch, order = self._place_order(client, vheaders, cheaders)

        resp = client.post(
            f"/api/v1/vendor/orders/{order['id']}/transition", headers=vheaders, json={"to_status": "PREPARING"}
        )
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "INVALID_TRANSITION"

    def test_vendor_cannot_cancel_via_transition_endpoint(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        _branch, order = self._place_order(client, vheaders, cheaders)

        resp = client.post(
            f"/api/v1/vendor/orders/{order['id']}/transition", headers=vheaders, json={"to_status": "CANCELLED"}
        )
        assert resp.status_code == 422

    def test_vendor_cannot_transition_another_vendors_order(self, client, vendor, vendor2, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        _branch, order = self._place_order(client, vheaders, cheaders)

        v2headers = login_as(client, "vendor2@example.com")
        resp = client.post(
            f"/api/v1/vendor/orders/{order['id']}/transition", headers=v2headers, json={"to_status": "VENDOR_ACCEPTED"}
        )
        assert resp.status_code == 404

    def test_transition_is_recorded_in_status_history_with_actor(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        _branch, order = self._place_order(client, vheaders, cheaders)
        client.post(
            f"/api/v1/vendor/orders/{order['id']}/transition", headers=vheaders,
            json={"to_status": "VENDOR_ACCEPTED", "reason": "Kitchen confirmed"},
        )

        history = client.get(
            f"/api/v1/vendor/orders/{order['id']}/status-history", headers=vheaders
        ).get_json()["data"]["history"]
        last = history[-1]
        assert last["to_status"] == "VENDOR_ACCEPTED"
        assert last["reason"] == "Kitchen confirmed"
        assert last["changed_by_role"] == "VENDOR"
