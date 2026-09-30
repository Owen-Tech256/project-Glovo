class _CheckoutFixtures:
    def _setup_branch_product(self, client, headers, price="9.99", availability="AVAILABLE",
                               lat=40.7128, lng=-74.0060, radius=5000, branch_name="Branch"):
        branch = client.post(
            "/api/v1/vendors/me/branches",
            headers=headers,
            json={"name": branch_name, "address": "1 Main St", "latitude": lat, "longitude": lng},
        ).get_json()["data"]["branch"]
        client.post(
            f"/api/v1/vendors/me/branches/{branch['id']}/zones",
            headers=headers,
            json={"name": "zone", "center_latitude": lat, "center_longitude": lng, "radius_meters": radius},
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
            json={"availability_status": availability},
        )
        return branch, product

    def _make_address(self, client, headers, lat=40.7128, lng=-74.0060, **overrides):
        payload = {
            "label": "Home",
            "recipient_name": "Cara Customer",
            "phone": "+12025550123",
            "address_line1": "123 Main St",
            "city": "New York",
            "country": "USA",
            "latitude": lat,
            "longitude": lng,
        }
        payload.update(overrides)
        return client.post("/api/v1/addresses", headers=headers, json=payload).get_json()["data"]["address"]

    def _full_setup(self, client, vheaders, cheaders, quantity=2, price="9.99"):
        """Vendor branch+product+zone, customer address, one item in cart.
        Returns (branch, product, address)."""
        branch, product = self._setup_branch_product(client, vheaders, price=price)
        address = self._make_address(client, cheaders)
        client.post(
            "/api/v1/cart/items", headers=cheaders,
            json={"branch_id": branch["id"], "product_id": product["id"], "quantity": quantity},
        )
        return branch, product, address


class TestCheckoutValidateAndSummary(_CheckoutFixtures):
    def test_validate_passes_for_a_valid_cart(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, _product, address = self._full_setup(client, vheaders, cheaders)

        resp = client.post(
            "/api/v1/checkout/validate", headers=cheaders,
            json={"branch_id": branch["id"], "address_id": address["id"]},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["is_valid"] is True
        assert data["issues"] == []
        assert data["subtotal"] == "19.98"

    def test_validate_flags_empty_cart(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, _product = self._setup_branch_product(client, vheaders)
        address = self._make_address(client, cheaders)

        resp = client.post(
            "/api/v1/checkout/validate", headers=cheaders,
            json={"branch_id": branch["id"], "address_id": address["id"]},
        )
        data = resp.get_json()["data"]
        assert data["is_valid"] is False
        assert data["issues"][0]["reason"] == "CART_EMPTY"

    def test_validate_flags_address_out_of_delivery_range(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, product = self._setup_branch_product(client, vheaders, radius=1000)
        # ~40km away - outside the 1km zone.
        address = self._make_address(client, cheaders, lat=41.0000, lng=-74.0060)
        client.post(
            "/api/v1/cart/items", headers=cheaders,
            json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 1},
        )

        resp = client.post(
            "/api/v1/checkout/validate", headers=cheaders,
            json={"branch_id": branch["id"], "address_id": address["id"]},
        )
        data = resp.get_json()["data"]
        assert data["is_valid"] is False
        assert {i["reason"] for i in data["issues"]} == {"ADDRESS_OUT_OF_RANGE"}

    def test_checkout_summary_includes_fees_and_total(self, client, vendor, customer, login_as, app):
        app.config["DELIVERY_FEE_FLAT"] = "3.00"
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, _product, address = self._full_setup(client, vheaders, cheaders, quantity=1, price="10.00")

        resp = client.get(f"/api/v1/checkout/summary?branch_id={branch['id']}&address_id={address['id']}", headers=cheaders)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["subtotal"] == "10.00"
        assert data["fees"] == "3.00"
        assert data["total"] == "13.00"

    def test_checkout_requires_owned_address(self, client, vendor, customer, customer2, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, product = self._setup_branch_product(client, vheaders)
        cheaders2 = login_as(client, "customer2@example.com")
        other_address = self._make_address(client, cheaders2)

        resp = client.post(
            "/api/v1/checkout/validate", headers=cheaders,
            json={"branch_id": branch["id"], "address_id": other_address["id"]},
        )
        assert resp.status_code == 404


class TestOrderCreation(_CheckoutFixtures):
    def test_customer_can_place_order(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, _product, address = self._full_setup(client, vheaders, cheaders, quantity=2, price="9.99")

        resp = client.post(
            "/api/v1/orders", headers=cheaders,
            json={"branch_id": branch["id"], "address_id": address["id"]},
        )
        assert resp.status_code == 201
        order = resp.get_json()["data"]["order"]
        # Phase 5: an order now starts PENDING_PAYMENT and only a real
        # payment (see test_payments.py) moves it to PAYMENT_CONFIRMED.
        assert order["status"] == "PENDING_PAYMENT"
        assert order["subtotal"] == "19.98"
        assert len(order["items"]) == 1
        assert order["items"][0]["quantity"] == 2
        assert order["delivery_address"]["city"] == "New York"
        assert order["order_number"].startswith("ORD-")

    def test_placing_order_converts_the_cart(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, _product, address = self._full_setup(client, vheaders, cheaders)
        client.post("/api/v1/orders", headers=cheaders, json={"branch_id": branch["id"], "address_id": address["id"]})

        after = client.get(f"/api/v1/cart?branch_id={branch['id']}", headers=cheaders).get_json()["data"]["cart"]
        assert after["items"] == []

    def test_cannot_place_order_with_empty_cart(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, _product = self._setup_branch_product(client, vheaders)
        address = self._make_address(client, cheaders)

        resp = client.post(
            "/api/v1/orders", headers=cheaders,
            json={"branch_id": branch["id"], "address_id": address["id"]},
        )
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "CART_EMPTY"

    def test_order_creation_records_full_status_history(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, _product, address = self._full_setup(client, vheaders, cheaders)
        order = client.post(
            "/api/v1/orders", headers=cheaders, json={"branch_id": branch["id"], "address_id": address["id"]}
        ).get_json()["data"]["order"]

        resp = client.get(f"/api/v1/orders/{order['id']}/status-history", headers=cheaders)
        history = resp.get_json()["data"]["history"]
        transitions = [(h["from_status"], h["to_status"]) for h in history]
        # Phase 5: order creation no longer auto-confirms payment - that
        # transition is now driven by an actual payment (test_payments.py
        # covers the full CREATED -> PENDING_PAYMENT -> PAYMENT_CONFIRMED
        # history once a payment succeeds).
        assert transitions == [
            (None, "CREATED"),
            ("CREATED", "PENDING_PAYMENT"),
        ]

    def test_repeated_idempotency_key_returns_same_order(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, product, address = self._full_setup(client, vheaders, cheaders)

        payload = {"branch_id": branch["id"], "address_id": address["id"], "idempotency_key": "retry-key-1"}
        first = client.post("/api/v1/orders", headers=cheaders, json=payload)
        assert first.status_code == 201
        first_order = first.get_json()["data"]["order"]

        # Confirm a retried submission returns the ORIGINAL order rather than
        # creating a second one, even if the cart has since changed.
        client.post(
            "/api/v1/cart/items", headers=cheaders,
            json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 1},
        )
        second = client.post("/api/v1/orders", headers=cheaders, json=payload)
        assert second.status_code == 200
        second_order = second.get_json()["data"]["order"]
        assert second_order["id"] == first_order["id"]

        all_orders = client.get("/api/v1/orders", headers=cheaders).get_json()["data"]["orders"]
        assert len(all_orders) == 1

    def test_order_creation_requires_valid_checkout(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, product = self._setup_branch_product(client, vheaders, radius=1000)
        address = self._make_address(client, cheaders, lat=41.0000, lng=-74.0060)
        client.post(
            "/api/v1/cart/items", headers=cheaders,
            json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 1},
        )
        resp = client.post(
            "/api/v1/orders", headers=cheaders,
            json={"branch_id": branch["id"], "address_id": address["id"]},
        )
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "CHECKOUT_INVALID"


class TestCustomerOrderAccess(_CheckoutFixtures):
    def _place_order(self, client, vheaders, cheaders, **kwargs):
        branch, _product, address = self._full_setup(client, vheaders, cheaders, **kwargs)
        order = client.post(
            "/api/v1/orders", headers=cheaders, json={"branch_id": branch["id"], "address_id": address["id"]}
        ).get_json()["data"]["order"]
        # Phase 5: pay for the order so tests that need a vendor-actionable
        # order (PAYMENT_CONFIRMED) keep working - PAYMENT_CONFIRMED is
        # still a cancellable state, so this doesn't affect the cancel
        # tests that reuse this helper.
        client.post("/api/v1/payments", headers=cheaders, json={"order_id": order["id"]})
        order = client.get(f"/api/v1/orders/{order['id']}", headers=cheaders).get_json()["data"]["order"]
        return branch, order

    def test_customer_can_list_own_orders(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        self._place_order(client, vheaders, cheaders)

        resp = client.get("/api/v1/orders", headers=cheaders)
        assert resp.status_code == 200
        assert len(resp.get_json()["data"]["orders"]) == 1

    def test_customer_cannot_view_another_customers_order(self, client, vendor, customer, customer2, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        _branch, order = self._place_order(client, vheaders, cheaders)

        cheaders2 = login_as(client, "customer2@example.com")
        resp = client.get(f"/api/v1/orders/{order['id']}", headers=cheaders2)
        assert resp.status_code == 404

    def test_customer_can_cancel_early_stage_order(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        _branch, order = self._place_order(client, vheaders, cheaders)

        resp = client.post(f"/api/v1/orders/{order['id']}/cancel", headers=cheaders, json={"reason": "Changed my mind"})
        assert resp.status_code == 200
        cancelled = resp.get_json()["data"]["order"]
        assert cancelled["status"] == "CANCELLED"
        assert cancelled["cancellation_reason"] == "Changed my mind"

    def test_customer_cannot_cancel_order_once_preparing(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        _branch, order = self._place_order(client, vheaders, cheaders)

        client.post(f"/api/v1/vendor/orders/{order['id']}/transition", headers=vheaders, json={"to_status": "VENDOR_ACCEPTED"})
        client.post(f"/api/v1/vendor/orders/{order['id']}/transition", headers=vheaders, json={"to_status": "PREPARING"})

        resp = client.post(f"/api/v1/orders/{order['id']}/cancel", headers=cheaders)
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "NOT_CANCELLABLE"

    def test_cancelling_someone_elses_order_is_404(self, client, vendor, customer, customer2, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        _branch, order = self._place_order(client, vheaders, cheaders)

        cheaders2 = login_as(client, "customer2@example.com")
        resp = client.post(f"/api/v1/orders/{order['id']}/cancel", headers=cheaders2)
        assert resp.status_code == 404

    def test_order_list_can_filter_by_status(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        _branch, order = self._place_order(client, vheaders, cheaders)
        client.post(f"/api/v1/orders/{order['id']}/cancel", headers=cheaders)

        active = client.get("/api/v1/orders?status=PAYMENT_CONFIRMED", headers=cheaders).get_json()["data"]["orders"]
        cancelled = client.get("/api/v1/orders?status=CANCELLED", headers=cheaders).get_json()["data"]["orders"]
        assert active == []
        assert len(cancelled) == 1
