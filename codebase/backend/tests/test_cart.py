class TestCart:
    def _setup_branch_product(self, client, headers, price="9.99", availability="AVAILABLE", branch_name="Branch"):
        branch = client.post(
            "/api/v1/vendors/me/branches",
            headers=headers,
            json={"name": branch_name, "address": "1 Main St", "latitude": 40.7128, "longitude": -74.0060},
        ).get_json()["data"]["branch"]
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

    # --- Adding items -----------------------------------------------------

    def test_customer_can_add_item_to_cart(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        branch, product = self._setup_branch_product(client, vheaders)

        cheaders = login_as(client, "customer@example.com")
        resp = client.post(
            "/api/v1/cart/items", headers=cheaders,
            json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 2},
        )
        assert resp.status_code == 201
        cart = resp.get_json()["data"]["cart"]
        assert cart["item_count"] == 2
        assert cart["subtotal"] == "19.98"
        assert len(cart["items"]) == 1
        assert cart["items"][0]["quantity"] == 2

    def test_adding_same_product_twice_increments_quantity(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        branch, product = self._setup_branch_product(client, vheaders)
        cheaders = login_as(client, "customer@example.com")
        url = "/api/v1/cart/items"
        client.post(url, headers=cheaders, json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 1})
        resp = client.post(url, headers=cheaders, json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 2})

        cart = resp.get_json()["data"]["cart"]
        assert len(cart["items"]) == 1
        assert cart["items"][0]["quantity"] == 3

    def test_add_item_respects_configurable_max_quantity(self, client, vendor, customer, login_as, app):
        app.config["CART_MAX_ITEM_QUANTITY"] = 5
        vheaders = login_as(client, "vendor@example.com")
        branch, product = self._setup_branch_product(client, vheaders)
        cheaders = login_as(client, "customer@example.com")
        resp = client.post(
            "/api/v1/cart/items", headers=cheaders,
            json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 6},
        )
        assert resp.status_code == 422

    def test_incrementing_past_max_quantity_is_rejected(self, client, vendor, customer, login_as, app):
        app.config["CART_MAX_ITEM_QUANTITY"] = 5
        vheaders = login_as(client, "vendor@example.com")
        branch, product = self._setup_branch_product(client, vheaders)
        cheaders = login_as(client, "customer@example.com")
        url = "/api/v1/cart/items"
        client.post(url, headers=cheaders, json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 3})
        resp = client.post(url, headers=cheaders, json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 3})
        assert resp.status_code == 422

    def test_cannot_add_unavailable_product_to_cart(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        branch, product = self._setup_branch_product(client, vheaders, availability="UNAVAILABLE")
        cheaders = login_as(client, "customer@example.com")
        resp = client.post(
            "/api/v1/cart/items", headers=cheaders,
            json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 1},
        )
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "PRODUCT_UNAVAILABLE"

    def test_adding_item_to_nonexistent_branch_is_404(self, client, customer, login_as):
        cheaders = login_as(client, "customer@example.com")
        resp = client.post(
            "/api/v1/cart/items", headers=cheaders,
            json={"branch_id": "not-a-real-id", "product_id": "not-a-real-id", "quantity": 1},
        )
        assert resp.status_code == 404

    def test_non_customer_cannot_use_cart(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        resp = client.post(
            "/api/v1/cart/items", headers=headers,
            json={"branch_id": "x", "product_id": "y", "quantity": 1},
        )
        assert resp.status_code == 403

    # --- Multi-branch isolation ---------------------------------------------

    def test_items_from_different_branches_go_to_separate_carts(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        branch1, product1 = self._setup_branch_product(client, vheaders, branch_name="Branch 1")
        branch2, product2 = self._setup_branch_product(client, vheaders, branch_name="Branch 2")
        cheaders = login_as(client, "customer@example.com")
        url = "/api/v1/cart/items"
        client.post(url, headers=cheaders, json={"branch_id": branch1["id"], "product_id": product1["id"], "quantity": 1})
        client.post(url, headers=cheaders, json={"branch_id": branch2["id"], "product_id": product2["id"], "quantity": 1})

        resp = client.get("/api/v1/cart", headers=cheaders)
        carts = resp.get_json()["data"]["carts"]
        assert len(carts) == 2
        assert {c["branch_id"] for c in carts} == {branch1["id"], branch2["id"]}

    def test_get_cart_by_branch_returns_empty_shape_when_none_exists(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        branch, _ = self._setup_branch_product(client, vheaders)
        cheaders = login_as(client, "customer@example.com")
        resp = client.get(f"/api/v1/cart?branch_id={branch['id']}", headers=cheaders)
        assert resp.status_code == 200
        cart = resp.get_json()["data"]["cart"]
        assert cart["items"] == []
        assert cart["subtotal"] == "0"

    # --- Updating / removing -------------------------------------------------

    def test_customer_can_update_item_quantity(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        branch, product = self._setup_branch_product(client, vheaders)
        cheaders = login_as(client, "customer@example.com")
        cart = client.post(
            "/api/v1/cart/items", headers=cheaders,
            json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 1},
        ).get_json()["data"]["cart"]
        item_id = cart["items"][0]["id"]

        resp = client.patch(f"/api/v1/cart/items/{item_id}", headers=cheaders, json={"quantity": 4})
        assert resp.status_code == 200
        assert resp.get_json()["data"]["cart"]["items"][0]["quantity"] == 4

    def test_customer_can_remove_item(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        branch, product = self._setup_branch_product(client, vheaders)
        cheaders = login_as(client, "customer@example.com")
        cart = client.post(
            "/api/v1/cart/items", headers=cheaders,
            json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 1},
        ).get_json()["data"]["cart"]
        item_id = cart["items"][0]["id"]

        resp = client.delete(f"/api/v1/cart/items/{item_id}", headers=cheaders)
        assert resp.status_code == 200
        after = client.get(f"/api/v1/cart?branch_id={branch['id']}", headers=cheaders).get_json()["data"]["cart"]
        assert after["items"] == []

    def test_customer_cannot_modify_another_customers_cart_item(self, client, vendor, customer, customer2, login_as):
        vheaders = login_as(client, "vendor@example.com")
        branch, product = self._setup_branch_product(client, vheaders)
        cheaders1 = login_as(client, "customer@example.com")
        cart = client.post(
            "/api/v1/cart/items", headers=cheaders1,
            json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 1},
        ).get_json()["data"]["cart"]
        item_id = cart["items"][0]["id"]

        cheaders2 = login_as(client, "customer2@example.com")
        resp = client.patch(f"/api/v1/cart/items/{item_id}", headers=cheaders2, json={"quantity": 2})
        assert resp.status_code == 404

    def test_clear_cart_empties_items_but_keeps_cart(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        branch, product = self._setup_branch_product(client, vheaders)
        cheaders = login_as(client, "customer@example.com")
        client.post(
            "/api/v1/cart/items", headers=cheaders,
            json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 1},
        )
        resp = client.delete(f"/api/v1/cart?branch_id={branch['id']}", headers=cheaders)
        assert resp.status_code == 200
        after = client.get(f"/api/v1/cart?branch_id={branch['id']}", headers=cheaders).get_json()["data"]["cart"]
        assert after["items"] == []

    # --- Live pricing --------------------------------------------------------

    def test_cart_reflects_live_price_changes(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        branch, product = self._setup_branch_product(client, vheaders, price="10.00")
        cheaders = login_as(client, "customer@example.com")
        client.post(
            "/api/v1/cart/items", headers=cheaders,
            json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 1},
        )

        client.put(
            f"/api/v1/vendors/me/branches/{branch['id']}/products/{product['id']}",
            headers=vheaders,
            json={"availability_status": "AVAILABLE", "price_override": "12.00"},
        )

        cart = client.get(f"/api/v1/cart?branch_id={branch['id']}", headers=cheaders).get_json()["data"]["cart"]
        item = cart["items"][0]
        assert item["current_unit_price"] == "12.00"
        assert item["price_changed"] is True
        assert cart["subtotal"] == "12.00"

    def test_cart_flags_item_that_became_unavailable(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        branch, product = self._setup_branch_product(client, vheaders)
        cheaders = login_as(client, "customer@example.com")
        client.post(
            "/api/v1/cart/items", headers=cheaders,
            json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 1},
        )
        client.put(
            f"/api/v1/vendors/me/branches/{branch['id']}/products/{product['id']}",
            headers=vheaders,
            json={"availability_status": "UNAVAILABLE"},
        )

        cart = client.get(f"/api/v1/cart?branch_id={branch['id']}", headers=cheaders).get_json()["data"]["cart"]
        assert cart["has_issues"] is True
        assert cart["issues"][0]["reason"] == "PRODUCT_UNAVAILABLE"
        # Excluded from the priced subtotal, not silently deleted from the cart.
        assert len(cart["items"]) == 1
        assert cart["subtotal"] == "0"
