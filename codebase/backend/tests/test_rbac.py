from tests.support_fixtures import SupportFixtures


class _F(SupportFixtures):
    pass


class TestSeededRoles(_F):
    def test_super_admin_can_list_roles(self, client, super_admin, login_as):
        headers = login_as(client, "superadmin@example.com")
        resp = client.get("/api/v1/admin/roles", headers=headers)
        assert resp.status_code == 200
        names = {r["name"] for r in resp.get_json()["data"]["roles"]}
        assert names == {"SUPER_ADMIN", "OPERATIONS_ADMIN", "FINANCE_ADMIN", "SUPPORT_AGENT", "MODERATOR", "ANALYST"}

    def test_legacy_admin_with_no_role_has_full_access(self, client, admin, login_as):
        """An ADMIN account with no admin_role assigned (every Phase 1-6
        admin account, and any new one until a SUPER_ADMIN scopes it down)
        keeps unrestricted access - see User.admin_role_id docstring."""
        headers = login_as(client, "admin@example.com")
        resp = client.get("/api/v1/admin/roles", headers=headers)
        assert resp.status_code == 200

    def test_non_super_admin_cannot_manage_roles(self, client, operations_admin, login_as):
        headers = login_as(client, "ops@example.com")
        resp = client.get("/api/v1/admin/roles", headers=headers)
        assert resp.status_code == 403

    def test_customer_cannot_touch_admin_routes_at_all(self, client, customer, login_as):
        headers = login_as(client, "customer@example.com")
        resp = client.get("/api/v1/admin/roles", headers=headers)
        assert resp.status_code == 403


class TestCustomRoles(_F):
    def test_create_role_with_unknown_permission_is_rejected(self, client, super_admin, login_as):
        headers = login_as(client, "superadmin@example.com")
        resp = client.post(
            "/api/v1/admin/roles", headers=headers,
            json={"name": "GHOST", "permission_keys": ["not.a.real.permission"]},
        )
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "UNKNOWN_PERMISSION"

    def test_create_and_assign_scoped_role(self, client, super_admin, admin, login_as):
        headers = login_as(client, "superadmin@example.com")
        create = client.post(
            "/api/v1/admin/roles", headers=headers,
            json={"name": "READ_ONLY_ANALYST", "description": "Just analytics.", "permission_keys": ["analytics.view"]},
        )
        assert create.status_code == 201
        role = create.get_json()["data"]["role"]
        assert role["permissions"] == ["analytics.view"]

        # `admin` currently has NULL admin_role (unrestricted) - once
        # explicitly scoped down, it should lose access outside that scope.
        admin_public_id = client.get("/api/v1/auth/me", headers=login_as(client, "admin@example.com")).get_json()["data"]["user"]["id"]
        assign = client.patch(
            f"/api/v1/admin/staff/{admin_public_id}/role", headers=headers, json={"role_id": role["id"]},
        )
        assert assign.status_code == 200
        assert assign.get_json()["data"]["staff"]["admin_role"] == "READ_ONLY_ANALYST"

        scoped_headers = login_as(client, "admin@example.com")
        allowed = client.get("/api/v1/analytics/overview", headers=scoped_headers)
        assert allowed.status_code == 200
        denied = client.get("/api/v1/admin/support/tickets", headers=scoped_headers)
        assert denied.status_code == 403

    def test_cannot_assign_admin_role_to_a_non_admin_user(self, client, super_admin, customer, login_as):
        headers = login_as(client, "superadmin@example.com")
        roles = client.get("/api/v1/admin/roles", headers=headers).get_json()["data"]["roles"]
        analyst_role_id = next(r["id"] for r in roles if r["name"] == "ANALYST")
        customer_public_id = client.get("/api/v1/auth/me", headers=login_as(client, "customer@example.com")).get_json()["data"]["user"]["id"]

        resp = client.patch(
            f"/api/v1/admin/staff/{customer_public_id}/role", headers=headers, json={"role_id": analyst_role_id},
        )
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "NOT_AN_ADMIN"

    def test_super_admin_permissions_cannot_be_narrowed(self, client, super_admin, login_as):
        headers = login_as(client, "superadmin@example.com")
        roles = client.get("/api/v1/admin/roles", headers=headers).get_json()["data"]["roles"]
        super_role_id = next(r["id"] for r in roles if r["name"] == "SUPER_ADMIN")

        resp = client.patch(
            f"/api/v1/admin/roles/{super_role_id}", headers=headers, json={"permission_keys": ["analytics.view"]},
        )
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "ROLE_IMMUTABLE"

    def test_permission_list_endpoint(self, client, super_admin, login_as):
        headers = login_as(client, "superadmin@example.com")
        resp = client.get("/api/v1/admin/permissions", headers=headers)
        assert resp.status_code == 200
        keys = {p["key"] for p in resp.get_json()["data"]["permissions"]}
        assert "support.manage" in keys
        assert "disputes.financial_action" in keys
