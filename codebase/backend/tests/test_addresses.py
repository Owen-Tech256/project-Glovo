class TestCustomerAddresses:
    def _payload(self, **overrides):
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
        payload.update(overrides)
        return payload

    def test_customer_can_create_address(self, client, customer, login_as):
        headers = login_as(client, "customer@example.com")
        resp = client.post("/api/v1/addresses", headers=headers, json=self._payload())
        assert resp.status_code == 201
        assert resp.get_json()["data"]["address"]["label"] == "Home"

    def test_non_customer_cannot_create_address(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        resp = client.post("/api/v1/addresses", headers=headers, json=self._payload())
        assert resp.status_code == 403

    def test_address_requires_valid_coordinates(self, client, customer, login_as):
        headers = login_as(client, "customer@example.com")
        resp = client.post("/api/v1/addresses", headers=headers, json=self._payload(latitude=999))
        assert resp.status_code == 422

    def test_first_address_is_default_automatically(self, client, customer, login_as):
        headers = login_as(client, "customer@example.com")
        resp = client.post("/api/v1/addresses", headers=headers, json=self._payload(is_default=False))
        assert resp.get_json()["data"]["address"]["is_default"] is True

    def test_only_one_default_address_at_a_time(self, client, customer, login_as):
        headers = login_as(client, "customer@example.com")
        client.post("/api/v1/addresses", headers=headers, json=self._payload(label="Home"))
        second = client.post(
            "/api/v1/addresses", headers=headers, json=self._payload(label="Work", is_default=True)
        ).get_json()["data"]["address"]
        assert second["is_default"] is True

        addresses = client.get("/api/v1/addresses", headers=headers).get_json()["data"]["addresses"]
        defaults = [a for a in addresses if a["is_default"]]
        assert len(defaults) == 1
        assert defaults[0]["label"] == "Work"

    def test_cannot_unset_only_default_address(self, client, customer, login_as):
        headers = login_as(client, "customer@example.com")
        addr = client.post("/api/v1/addresses", headers=headers, json=self._payload()).get_json()["data"]["address"]

        resp = client.patch(f"/api/v1/addresses/{addr['id']}", headers=headers, json={"is_default": False})
        assert resp.get_json()["data"]["address"]["is_default"] is True

    def test_deleting_default_promotes_another_address(self, client, customer, login_as):
        headers = login_as(client, "customer@example.com")
        first = client.post(
            "/api/v1/addresses", headers=headers, json=self._payload(label="Home")
        ).get_json()["data"]["address"]
        second = client.post(
            "/api/v1/addresses", headers=headers, json=self._payload(label="Work")
        ).get_json()["data"]["address"]

        client.delete(f"/api/v1/addresses/{first['id']}", headers=headers)

        remaining = client.get("/api/v1/addresses", headers=headers).get_json()["data"]["addresses"]
        assert len(remaining) == 1
        assert remaining[0]["id"] == second["id"]
        assert remaining[0]["is_default"] is True

    def test_customer_cannot_access_another_customers_address(self, client, customer, customer2, login_as):
        headers1 = login_as(client, "customer@example.com")
        addr = client.post("/api/v1/addresses", headers=headers1, json=self._payload()).get_json()["data"][
            "address"
        ]

        headers2 = login_as(client, "customer2@example.com")
        resp = client.get(f"/api/v1/addresses/{addr['id']}", headers=headers2)
        assert resp.status_code == 404

    def test_customer_cannot_delete_another_customers_address(self, client, customer, customer2, login_as):
        headers1 = login_as(client, "customer@example.com")
        addr = client.post("/api/v1/addresses", headers=headers1, json=self._payload()).get_json()["data"][
            "address"
        ]

        headers2 = login_as(client, "customer2@example.com")
        resp = client.delete(f"/api/v1/addresses/{addr['id']}", headers=headers2)
        assert resp.status_code == 404

    def test_customer_can_update_own_address(self, client, customer, login_as):
        headers = login_as(client, "customer@example.com")
        addr = client.post("/api/v1/addresses", headers=headers, json=self._payload()).get_json()["data"][
            "address"
        ]
        resp = client.patch(
            f"/api/v1/addresses/{addr['id']}", headers=headers, json={"city": "Brooklyn"}
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["address"]["city"] == "Brooklyn"
