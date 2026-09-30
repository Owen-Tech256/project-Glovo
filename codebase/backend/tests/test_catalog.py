class TestCategories:
    def test_vendor_can_create_category(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        resp = client.post("/api/v1/vendors/me/categories", headers=headers, json={"name": "Pizzas"})
        assert resp.status_code == 201
        data = resp.get_json()["data"]["category"]
        assert data["name"] == "Pizzas"
        assert data["is_active"] is True

    def test_non_vendor_cannot_create_category(self, client, customer, login_as):
        headers = login_as(client, "customer@example.com")
        resp = client.post("/api/v1/vendors/me/categories", headers=headers, json={"name": "Pizzas"})
        assert resp.status_code == 403

    def test_category_name_is_required(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        resp = client.post("/api/v1/vendors/me/categories", headers=headers, json={})
        assert resp.status_code == 422

    def test_vendor_cannot_access_another_vendors_category(self, client, vendor, vendor2, login_as):
        headers1 = login_as(client, "vendor@example.com")
        category = client.post(
            "/api/v1/vendors/me/categories", headers=headers1, json={"name": "Pizzas"}
        ).get_json()["data"]["category"]

        headers2 = login_as(client, "vendor2@example.com")
        resp = client.get(f"/api/v1/vendors/me/categories/{category['id']}", headers=headers2)
        assert resp.status_code == 404

    def test_delete_category_deactivates_rather_than_removes(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        category = client.post(
            "/api/v1/vendors/me/categories", headers=headers, json={"name": "Pizzas"}
        ).get_json()["data"]["category"]

        resp = client.delete(f"/api/v1/vendors/me/categories/{category['id']}", headers=headers)
        assert resp.status_code == 200

        get_resp = client.get(f"/api/v1/vendors/me/categories/{category['id']}", headers=headers)
        assert get_resp.get_json()["data"]["category"]["is_active"] is False

    def test_public_category_list_excludes_inactive(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        category = client.post(
            "/api/v1/vendors/me/categories", headers=headers, json={"name": "Pizzas"}
        ).get_json()["data"]["category"]
        client.delete(f"/api/v1/vendors/me/categories/{category['id']}", headers=headers)

        me = client.get("/api/v1/vendors/me", headers=headers).get_json()["data"]["vendor"]
        resp = client.get(f"/api/v1/vendors/{me['id']}/categories")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["categories"] == []


class TestProducts:
    def _make_category(self, client, headers, name="Pizzas"):
        return client.post("/api/v1/vendors/me/categories", headers=headers, json={"name": name}).get_json()[
            "data"
        ]["category"]

    def test_vendor_can_create_product(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        category = self._make_category(client, headers)
        resp = client.post(
            "/api/v1/vendors/me/products",
            headers=headers,
            json={"category_id": category["id"], "name": "Margherita", "price": "9.99"},
        )
        assert resp.status_code == 201
        data = resp.get_json()["data"]["product"]
        assert data["name"] == "Margherita"
        assert data["price"] == "9.99"
        assert data["status"] == "ACTIVE"

    def test_product_rejects_negative_price(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        category = self._make_category(client, headers)
        resp = client.post(
            "/api/v1/vendors/me/products",
            headers=headers,
            json={"category_id": category["id"], "name": "Margherita", "price": "-5.00"},
        )
        assert resp.status_code == 422

    def test_product_rejects_missing_category(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        resp = client.post(
            "/api/v1/vendors/me/products",
            headers=headers,
            json={"category_id": "not-a-real-id", "name": "Margherita", "price": "9.99"},
        )
        assert resp.status_code == 404

    def test_vendor_cannot_assign_product_to_another_vendors_category(self, client, vendor, vendor2, login_as):
        headers1 = login_as(client, "vendor@example.com")
        category = self._make_category(client, headers1)

        headers2 = login_as(client, "vendor2@example.com")
        resp = client.post(
            "/api/v1/vendors/me/products",
            headers=headers2,
            json={"category_id": category["id"], "name": "Hijack Pizza", "price": "1.00"},
        )
        assert resp.status_code == 404

    def test_delete_product_archives_rather_than_removes(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        category = self._make_category(client, headers)
        product = client.post(
            "/api/v1/vendors/me/products",
            headers=headers,
            json={"category_id": category["id"], "name": "Margherita", "price": "9.99"},
        ).get_json()["data"]["product"]

        resp = client.delete(f"/api/v1/vendors/me/products/{product['id']}", headers=headers)
        assert resp.status_code == 200
        get_resp = client.get(f"/api/v1/vendors/me/products/{product['id']}", headers=headers)
        assert get_resp.get_json()["data"]["product"]["status"] == "ARCHIVED"

    def test_public_can_browse_active_category_products(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        category = self._make_category(client, headers)
        client.post(
            "/api/v1/vendors/me/products",
            headers=headers,
            json={"category_id": category["id"], "name": "Margherita", "price": "9.99"},
        )
        resp = client.get(f"/api/v1/categories/{category['id']}/products")
        assert resp.status_code == 200
        assert len(resp.get_json()["data"]["products"]) == 1

    def test_public_product_browsing_excludes_archived(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        category = self._make_category(client, headers)
        product = client.post(
            "/api/v1/vendors/me/products",
            headers=headers,
            json={"category_id": category["id"], "name": "Margherita", "price": "9.99"},
        ).get_json()["data"]["product"]
        client.delete(f"/api/v1/vendors/me/products/{product['id']}", headers=headers)

        resp = client.get(f"/api/v1/categories/{category['id']}/products")
        assert resp.get_json()["data"]["products"] == []


class TestProductImages:
    def _make_product(self, client, headers):
        category = client.post(
            "/api/v1/vendors/me/categories", headers=headers, json={"name": "Pizzas"}
        ).get_json()["data"]["category"]
        return client.post(
            "/api/v1/vendors/me/products",
            headers=headers,
            json={"category_id": category["id"], "name": "Margherita", "price": "9.99"},
        ).get_json()["data"]["product"]

    def test_vendor_can_add_image_to_own_product(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        product = self._make_product(client, headers)
        resp = client.post(
            f"/api/v1/vendors/me/products/{product['id']}/images",
            headers=headers,
            json={"image_url": "https://example.com/pizza.jpg", "alt_text": "Margherita pizza"},
        )
        assert resp.status_code == 201
        assert resp.get_json()["data"]["image"]["image_url"] == "https://example.com/pizza.jpg"

    def test_image_appears_on_product_detail(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        product = self._make_product(client, headers)
        client.post(
            f"/api/v1/vendors/me/products/{product['id']}/images",
            headers=headers,
            json={"image_url": "https://example.com/pizza.jpg"},
        )
        resp = client.get(f"/api/v1/vendors/me/products/{product['id']}", headers=headers)
        assert len(resp.get_json()["data"]["product"]["images"]) == 1

    def test_vendor_cannot_add_image_to_another_vendors_product(self, client, vendor, vendor2, login_as):
        headers1 = login_as(client, "vendor@example.com")
        product = self._make_product(client, headers1)

        headers2 = login_as(client, "vendor2@example.com")
        resp = client.post(
            f"/api/v1/vendors/me/products/{product['id']}/images",
            headers=headers2,
            json={"image_url": "https://example.com/hijack.jpg"},
        )
        assert resp.status_code == 404

    def test_vendor_can_delete_own_product_image(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        product = self._make_product(client, headers)
        image = client.post(
            f"/api/v1/vendors/me/products/{product['id']}/images",
            headers=headers,
            json={"image_url": "https://example.com/pizza.jpg"},
        ).get_json()["data"]["image"]

        resp = client.delete(
            f"/api/v1/vendors/me/products/{product['id']}/images/{image['id']}", headers=headers
        )
        assert resp.status_code == 200


class TestBranchProducts:
    def _setup(self, client, headers):
        branch = client.post(
            "/api/v1/vendors/me/branches",
            headers=headers,
            json={"name": "Branch", "address": "1 Main St", "latitude": 40.7128, "longitude": -74.0060},
        ).get_json()["data"]["branch"]
        category = client.post(
            "/api/v1/vendors/me/categories", headers=headers, json={"name": "Pizzas"}
        ).get_json()["data"]["category"]
        product = client.post(
            "/api/v1/vendors/me/products",
            headers=headers,
            json={"category_id": category["id"], "name": "Margherita", "price": "9.99"},
        ).get_json()["data"]["product"]
        return branch, product

    def test_vendor_can_set_branch_product_availability(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        branch, product = self._setup(client, headers)

        resp = client.put(
            f"/api/v1/vendors/me/branches/{branch['id']}/products/{product['id']}",
            headers=headers,
            json={"availability_status": "AVAILABLE", "price_override": "8.50"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]["branch_product"]
        assert data["availability_status"] == "AVAILABLE"
        assert data["price_override"] == "8.50"
        assert data["effective_price"] == "8.50"

    def test_effective_price_falls_back_to_product_price(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        branch, product = self._setup(client, headers)
        resp = client.put(
            f"/api/v1/vendors/me/branches/{branch['id']}/products/{product['id']}",
            headers=headers,
            json={"availability_status": "AVAILABLE"},
        )
        assert resp.get_json()["data"]["branch_product"]["effective_price"] == "9.99"

    def test_setting_availability_twice_upserts_not_duplicates(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        branch, product = self._setup(client, headers)
        url = f"/api/v1/vendors/me/branches/{branch['id']}/products/{product['id']}"
        client.put(url, headers=headers, json={"availability_status": "AVAILABLE"})
        client.put(url, headers=headers, json={"availability_status": "UNAVAILABLE"})

        list_resp = client.get(f"/api/v1/vendors/me/branches/{branch['id']}/products", headers=headers)
        links = list_resp.get_json()["data"]["branch_products"]
        assert len(links) == 1
        assert links[0]["availability_status"] == "UNAVAILABLE"

    def test_public_branch_catalog_only_shows_available_products(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        branch, product = self._setup(client, headers)
        client.put(
            f"/api/v1/vendors/me/branches/{branch['id']}/products/{product['id']}",
            headers=headers,
            json={"availability_status": "UNAVAILABLE"},
        )
        resp = client.get(f"/api/v1/branches/{branch['id']}/products")
        assert resp.get_json()["data"]["branch_products"] == []

        client.put(
            f"/api/v1/vendors/me/branches/{branch['id']}/products/{product['id']}",
            headers=headers,
            json={"availability_status": "AVAILABLE"},
        )
        resp2 = client.get(f"/api/v1/branches/{branch['id']}/products")
        assert len(resp2.get_json()["data"]["branch_products"]) == 1

    def test_vendor_can_remove_product_from_branch(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        branch, product = self._setup(client, headers)
        url = f"/api/v1/vendors/me/branches/{branch['id']}/products/{product['id']}"
        client.put(url, headers=headers, json={"availability_status": "AVAILABLE"})
        resp = client.delete(url, headers=headers)
        assert resp.status_code == 200

        list_resp = client.get(f"/api/v1/vendors/me/branches/{branch['id']}/products", headers=headers)
        assert list_resp.get_json()["data"]["branch_products"] == []

    def test_vendor_cannot_set_availability_on_another_vendors_branch(self, client, vendor, vendor2, login_as):
        headers1 = login_as(client, "vendor@example.com")
        branch, product = self._setup(client, headers1)

        headers2 = login_as(client, "vendor2@example.com")
        resp = client.put(
            f"/api/v1/vendors/me/branches/{branch['id']}/products/{product['id']}",
            headers=headers2,
            json={"availability_status": "AVAILABLE"},
        )
        assert resp.status_code == 404
