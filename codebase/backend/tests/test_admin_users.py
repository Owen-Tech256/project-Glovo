from tests.support_fixtures import SupportFixtures


class _F(SupportFixtures):
    pass


class TestAdminUserManagement(_F):
    def test_admin_can_list_and_filter_users(self, client, admin, customer, vendor, login_as):
        headers = login_as(client, "admin@example.com")
        resp = client.get("/api/v1/admin/users", headers=headers, query_string={"role": "CUSTOMER"})
        assert resp.status_code == 200
        users = resp.get_json()["data"]["users"]
        assert all(u["role"] == "CUSTOMER" for u in users)
        assert any(u["email"] == "customer@example.com" for u in users)

    def test_admin_can_search_by_name_or_email(self, client, admin, customer, login_as):
        headers = login_as(client, "admin@example.com")
        resp = client.get("/api/v1/admin/users", headers=headers, query_string={"q": "Cara"})
        users = resp.get_json()["data"]["users"]
        assert any(u["full_name"] == "Cara Customer" for u in users)

    def test_admin_can_view_user_detail_with_vendor_profile(self, client, admin, vendor, login_as):
        headers = login_as(client, "admin@example.com")
        vheaders = login_as(client, "vendor@example.com")
        vendor_public_id = client.get("/api/v1/auth/me", headers=vheaders).get_json()["data"]["user"]["id"]
        client.get("/api/v1/vendors/me", headers=vheaders)  # provisions the Vendor profile lazily
        resp = client.get(f"/api/v1/admin/users/{vendor_public_id}", headers=headers)
        assert resp.status_code == 200
        assert "vendor" in resp.get_json()["data"]["user"]

    def test_admin_can_suspend_and_reactivate_a_user(self, client, admin, customer, login_as):
        headers = login_as(client, "admin@example.com")
        customer_public_id = client.get("/api/v1/auth/me", headers=login_as(client, "customer@example.com")).get_json()["data"]["user"]["id"]

        suspend = client.patch(
            f"/api/v1/admin/users/{customer_public_id}/status", headers=headers,
            json={"status": "SUSPENDED", "reason": "Suspicious activity."},
        )
        assert suspend.status_code == 200
        assert suspend.get_json()["data"]["user"]["status"] == "SUSPENDED"

        reactivate = client.patch(
            f"/api/v1/admin/users/{customer_public_id}/status", headers=headers, json={"status": "ACTIVE"},
        )
        assert reactivate.status_code == 200
        assert reactivate.get_json()["data"]["user"]["status"] == "ACTIVE"

    def test_suspended_user_cannot_log_in(self, client, admin, customer, login_as):
        headers = login_as(client, "admin@example.com")
        customer_public_id = client.get("/api/v1/auth/me", headers=login_as(client, "customer@example.com")).get_json()["data"]["user"]["id"]
        client.patch(f"/api/v1/admin/users/{customer_public_id}/status", headers=headers, json={"status": "SUSPENDED"})

        resp = client.post("/api/v1/auth/login", json={"identifier": "customer@example.com", "password": "Password123"})
        assert resp.status_code == 403

    def test_admin_cannot_modify_own_status(self, client, admin, login_as):
        headers = login_as(client, "admin@example.com")
        own_id = client.get("/api/v1/auth/me", headers=headers).get_json()["data"]["user"]["id"]
        resp = client.patch(f"/api/v1/admin/users/{own_id}/status", headers=headers, json={"status": "SUSPENDED"})
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "CANNOT_SELF_MODIFY"

    def test_status_change_is_audited(self, client, admin, customer, login_as):
        headers = login_as(client, "admin@example.com")
        customer_public_id = client.get("/api/v1/auth/me", headers=login_as(client, "customer@example.com")).get_json()["data"]["user"]["id"]
        client.patch(f"/api/v1/admin/users/{customer_public_id}/status", headers=headers,
                     json={"status": "SUSPENDED", "reason": "test"})

        events = client.get(
            "/api/v1/admin/audit/events", headers=headers,
            query_string={"entity_type": "USER", "entity_id": customer_public_id},
        ).get_json()["data"]["events"]
        assert any(e["action"] == "USER_STATUS_CHANGED" for e in events)

    def test_non_admin_cannot_access_user_management(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        resp = client.get("/api/v1/admin/users", headers=headers)
        assert resp.status_code == 403

    def test_scoped_admin_without_users_manage_is_forbidden(self, client, moderator, login_as):
        headers = login_as(client, "moderator@example.com")
        resp = client.get("/api/v1/admin/users", headers=headers)
        assert resp.status_code == 403
