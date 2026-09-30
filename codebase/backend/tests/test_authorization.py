class TestRoleAuthorization:
    def test_customer_cannot_access_admin_endpoint(self, client, customer, login_as):
        headers = login_as(client, "customer@example.com")
        resp = client.get("/api/v1/admin/stats", headers=headers)
        assert resp.status_code == 403
        assert resp.get_json()["error"]["code"] == "FORBIDDEN"

    def test_vendor_cannot_access_admin_endpoint(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        resp = client.get("/api/v1/admin/stats", headers=headers)
        assert resp.status_code == 403

    def test_rider_cannot_access_admin_endpoint(self, client, rider, login_as):
        headers = login_as(client, "rider@example.com")
        resp = client.get("/api/v1/admin/stats", headers=headers)
        assert resp.status_code == 403

    def test_admin_can_access_admin_endpoint(self, client, admin, login_as):
        headers = login_as(client, "admin@example.com")
        resp = client.get("/api/v1/admin/stats", headers=headers)
        assert resp.status_code == 200
        assert "users_by_role" in resp.get_json()["data"]

    def test_admin_stats_requires_authentication(self, client):
        resp = client.get("/api/v1/admin/stats")
        assert resp.status_code == 401

    def test_customer_cannot_list_users(self, client, customer, login_as):
        headers = login_as(client, "customer@example.com")
        resp = client.get("/api/v1/users", headers=headers)
        assert resp.status_code == 403

    def test_admin_can_list_users(self, client, admin, customer, login_as):
        headers = login_as(client, "admin@example.com")
        resp = client.get("/api/v1/users", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["pagination"]["total"] >= 2


class TestOwnershipProtection:
    def test_user_can_fetch_own_record_by_public_id(self, client, customer, login_as):
        headers = login_as(client, "customer@example.com")
        resp = client.get(f"/api/v1/users/{customer.public_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["user"]["email"] == "customer@example.com"

    def test_user_cannot_fetch_another_users_record_by_changing_url_id(self, client, customer, vendor, login_as):
        """The core ownership guarantee: changing the ID in the URL must not
        grant access to someone else's private resource."""
        headers = login_as(client, "customer@example.com")
        resp = client.get(f"/api/v1/users/{vendor.public_id}", headers=headers)
        assert resp.status_code == 403
        assert resp.get_json()["error"]["code"] == "FORBIDDEN"

    def test_rider_cannot_fetch_customers_record(self, client, rider, customer, login_as):
        headers = login_as(client, "rider@example.com")
        resp = client.get(f"/api/v1/users/{customer.public_id}", headers=headers)
        assert resp.status_code == 403

    def test_admin_can_fetch_any_users_record(self, client, admin, customer, login_as):
        headers = login_as(client, "admin@example.com")
        resp = client.get(f"/api/v1/users/{customer.public_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["user"]["email"] == "customer@example.com"

    def test_fetching_nonexistent_public_id_as_admin_returns_404(self, client, admin, login_as):
        headers = login_as(client, "admin@example.com")
        resp = client.get("/api/v1/users/00000000-0000-0000-0000-000000000000", headers=headers)
        assert resp.status_code == 404

    def test_ownership_check_requires_authentication(self, client, customer):
        resp = client.get(f"/api/v1/users/{customer.public_id}")
        assert resp.status_code == 401


class TestUpdateOwnProfile:
    def test_user_can_update_own_full_name(self, client, customer, login_as):
        headers = login_as(client, "customer@example.com")
        resp = client.patch("/api/v1/users/me", json={"full_name": "Cara C. Customer"}, headers=headers)
        body = resp.get_json()
        assert resp.status_code == 200
        assert body["data"]["user"]["full_name"] == "Cara C. Customer"

    def test_update_me_requires_authentication(self, client):
        resp = client.patch("/api/v1/users/me", json={"full_name": "Nope"})
        assert resp.status_code == 401

    def test_update_me_ignores_disallowed_fields(self, client, customer, login_as):
        """email, phone, role, and status are not self-service fields; the
        schema silently drops unknown/disallowed keys rather than erroring,
        so a client cannot escalate privilege via this endpoint."""
        headers = login_as(client, "customer@example.com")
        resp = client.patch(
            "/api/v1/users/me",
            json={"role": "ADMIN", "status": "ACTIVE", "full_name": "Still Cara"},
            headers=headers,
        )
        body = resp.get_json()
        assert resp.status_code == 200
        assert body["data"]["user"]["role"] == "CUSTOMER"
        assert body["data"]["user"]["full_name"] == "Still Cara"
