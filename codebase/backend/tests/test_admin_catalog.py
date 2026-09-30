class TestAdminVendorOversight:
    def test_non_admin_cannot_list_vendors(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        resp = client.get("/api/v1/admin/vendors", headers=headers)
        assert resp.status_code == 403

    def test_admin_can_list_vendors(self, client, vendor, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        client.get("/api/v1/vendors/me", headers=vheaders)  # lazily provisions the vendor

        aheaders = login_as(client, "admin@example.com")
        resp = client.get("/api/v1/admin/vendors", headers=aheaders)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["pagination"]["total"] >= 1

    def test_admin_can_filter_vendors_by_status(self, client, vendor, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        client.get("/api/v1/vendors/me", headers=vheaders)

        aheaders = login_as(client, "admin@example.com")
        resp = client.get("/api/v1/admin/vendors?status=SUSPENDED", headers=aheaders)
        assert resp.get_json()["data"]["pagination"]["total"] == 0

    def test_admin_can_view_vendor_detail(self, client, vendor, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        me = client.get("/api/v1/vendors/me", headers=vheaders).get_json()["data"]["vendor"]

        aheaders = login_as(client, "admin@example.com")
        resp = client.get(f"/api/v1/admin/vendors/{me['id']}", headers=aheaders)
        assert resp.status_code == 200
        assert "branch_count" in resp.get_json()["data"]

    def test_admin_can_suspend_vendor(self, client, vendor, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        me = client.get("/api/v1/vendors/me", headers=vheaders).get_json()["data"]["vendor"]

        aheaders = login_as(client, "admin@example.com")
        resp = client.patch(f"/api/v1/admin/vendors/{me['id']}/status", headers=aheaders, json={"status": "SUSPENDED"})
        assert resp.status_code == 200
        assert resp.get_json()["data"]["vendor"]["status"] == "SUSPENDED"

    def test_vendor_cannot_suspend_own_vendor_via_admin_route(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        me = client.get("/api/v1/vendors/me", headers=headers).get_json()["data"]["vendor"]
        resp = client.patch(f"/api/v1/admin/vendors/{me['id']}/status", headers=headers, json={"status": "SUSPENDED"})
        assert resp.status_code == 403

    def test_admin_can_view_vendor_branches(self, client, vendor, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        client.post(
            "/api/v1/vendors/me/branches",
            headers=vheaders,
            json={"name": "Branch", "address": "1 Main St", "latitude": 40.7128, "longitude": -74.0060},
        )
        me = client.get("/api/v1/vendors/me", headers=vheaders).get_json()["data"]["vendor"]

        aheaders = login_as(client, "admin@example.com")
        resp = client.get(f"/api/v1/admin/vendors/{me['id']}/branches", headers=aheaders)
        assert resp.status_code == 200
        assert len(resp.get_json()["data"]["branches"]) == 1

    def test_admin_can_suspend_a_branch(self, client, vendor, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        branch = client.post(
            "/api/v1/vendors/me/branches",
            headers=vheaders,
            json={"name": "Branch", "address": "1 Main St", "latitude": 40.7128, "longitude": -74.0060},
        ).get_json()["data"]["branch"]

        aheaders = login_as(client, "admin@example.com")
        resp = client.patch(
            f"/api/v1/admin/branches/{branch['id']}/status", headers=aheaders, json={"status": "SUSPENDED"}
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["branch"]["status"] == "SUSPENDED"

    def test_admin_can_view_vendor_catalog(self, client, vendor, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        category = client.post(
            "/api/v1/vendors/me/categories", headers=vheaders, json={"name": "Pizzas"}
        ).get_json()["data"]["category"]
        client.post(
            "/api/v1/vendors/me/products",
            headers=vheaders,
            json={"category_id": category["id"], "name": "Margherita", "price": "9.99"},
        )
        me = client.get("/api/v1/vendors/me", headers=vheaders).get_json()["data"]["vendor"]

        aheaders = login_as(client, "admin@example.com")
        resp = client.get(f"/api/v1/admin/vendors/{me['id']}/catalog", headers=aheaders)
        assert resp.status_code == 200
        categories = resp.get_json()["data"]["categories"]
        assert len(categories) == 1
        assert len(categories[0]["products"]) == 1
