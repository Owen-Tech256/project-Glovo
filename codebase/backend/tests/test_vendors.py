class TestVendorProfile:
    def test_vendor_profile_is_lazily_provisioned_on_first_access(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        resp = client.get("/api/v1/vendors/me", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()["data"]["vendor"]
        assert data["name"] == "Vic Vendor"
        assert data["status"] == "ACTIVE"

    def test_non_vendor_cannot_access_vendor_me(self, client, customer, login_as):
        headers = login_as(client, "customer@example.com")
        resp = client.get("/api/v1/vendors/me", headers=headers)
        assert resp.status_code == 403

    def test_vendor_me_requires_authentication(self, client):
        resp = client.get("/api/v1/vendors/me")
        assert resp.status_code == 401

    def test_vendor_can_update_own_profile(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        resp = client.patch(
            "/api/v1/vendors/me",
            headers=headers,
            json={"name": "Vic's Pizzeria", "description": "Best pizza in town", "phone": "+12025550123"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]["vendor"]
        assert data["name"] == "Vic's Pizzeria"
        assert data["description"] == "Best pizza in town"

    def test_vendor_update_rejects_invalid_phone(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        resp = client.patch("/api/v1/vendors/me", headers=headers, json={"phone": "not-a-phone"})
        assert resp.status_code == 422

    def test_public_can_view_active_vendor(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        client.patch("/api/v1/vendors/me", headers=headers, json={"name": "Vic's Pizzeria"})
        me = client.get("/api/v1/vendors/me", headers=headers).get_json()["data"]["vendor"]

        resp = client.get(f"/api/v1/vendors/{me['id']}")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["vendor"]["name"] == "Vic's Pizzeria"

    def test_public_cannot_view_suspended_vendor(self, client, vendor, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        me = client.get("/api/v1/vendors/me", headers=vheaders).get_json()["data"]["vendor"]

        aheaders = login_as(client, "admin@example.com")
        client.patch(f"/api/v1/admin/vendors/{me['id']}/status", headers=aheaders, json={"status": "SUSPENDED"})

        resp = client.get(f"/api/v1/vendors/{me['id']}")
        assert resp.status_code == 404


class TestBranches:
    def _create_branch(self, client, headers, **overrides):
        payload = {
            "name": "Downtown Branch",
            "address": "123 Main St",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "phone": "+12025550123",
        }
        payload.update(overrides)
        return client.post("/api/v1/vendors/me/branches", headers=headers, json=payload)

    def test_vendor_can_create_branch(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        resp = self._create_branch(client, headers)
        assert resp.status_code == 201
        data = resp.get_json()["data"]["branch"]
        assert data["name"] == "Downtown Branch"
        assert data["status"] == "ACTIVE"

    def test_branch_requires_valid_latitude(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        resp = self._create_branch(client, headers, latitude=200.0)
        assert resp.status_code == 422

    def test_branch_requires_valid_longitude(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        resp = self._create_branch(client, headers, longitude=-200.0)
        assert resp.status_code == 422

    def test_non_vendor_cannot_create_branch(self, client, customer, login_as):
        headers = login_as(client, "customer@example.com")
        resp = self._create_branch(client, headers)
        assert resp.status_code == 403

    def test_vendor_can_list_own_branches(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        self._create_branch(client, headers, name="Branch A")
        self._create_branch(client, headers, name="Branch B")
        resp = client.get("/api/v1/vendors/me/branches", headers=headers)
        assert resp.status_code == 200
        assert len(resp.get_json()["data"]["branches"]) == 2

    def test_vendor_cannot_access_another_vendors_branch(self, client, vendor, vendor2, login_as):
        headers1 = login_as(client, "vendor@example.com")
        branch = self._create_branch(client, headers1).get_json()["data"]["branch"]

        headers2 = login_as(client, "vendor2@example.com")
        resp = client.get(f"/api/v1/vendors/me/branches/{branch['id']}", headers=headers2)
        assert resp.status_code == 404

    def test_vendor_cannot_update_another_vendors_branch(self, client, vendor, vendor2, login_as):
        headers1 = login_as(client, "vendor@example.com")
        branch = self._create_branch(client, headers1).get_json()["data"]["branch"]

        headers2 = login_as(client, "vendor2@example.com")
        resp = client.patch(
            f"/api/v1/vendors/me/branches/{branch['id']}", headers=headers2, json={"name": "Hijacked"}
        )
        assert resp.status_code == 404

    def test_vendor_can_update_own_branch(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        branch = self._create_branch(client, headers).get_json()["data"]["branch"]
        resp = client.patch(
            f"/api/v1/vendors/me/branches/{branch['id']}", headers=headers, json={"name": "Renamed Branch"}
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["branch"]["name"] == "Renamed Branch"

    def test_delete_branch_closes_rather_than_removes(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        branch = self._create_branch(client, headers).get_json()["data"]["branch"]
        resp = client.delete(f"/api/v1/vendors/me/branches/{branch['id']}", headers=headers)
        assert resp.status_code == 200

        get_resp = client.get(f"/api/v1/vendors/me/branches/{branch['id']}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.get_json()["data"]["branch"]["status"] == "CLOSED"

    def test_public_branch_list_excludes_closed_branches(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        branch = self._create_branch(client, headers).get_json()["data"]["branch"]
        client.delete(f"/api/v1/vendors/me/branches/{branch['id']}", headers=headers)

        me = client.get("/api/v1/vendors/me", headers=headers).get_json()["data"]["vendor"]
        resp = client.get(f"/api/v1/vendors/{me['id']}/branches")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["branches"] == []


class TestDeliveryZones:
    def _create_branch(self, client, headers):
        payload = {"name": "Branch", "address": "1 Main St", "latitude": 40.7128, "longitude": -74.0060}
        return client.post("/api/v1/vendors/me/branches", headers=headers, json=payload).get_json()["data"]["branch"]

    def test_vendor_can_create_zone_on_own_branch(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        branch = self._create_branch(client, headers)
        resp = client.post(
            f"/api/v1/vendors/me/branches/{branch['id']}/zones",
            headers=headers,
            json={"name": "5km radius", "center_latitude": 40.7128, "center_longitude": -74.0060, "radius_meters": 5000},
        )
        assert resp.status_code == 201
        data = resp.get_json()["data"]["delivery_zone"]
        assert data["radius_meters"] == 5000
        assert data["status"] == "ACTIVE"

    def test_zone_rejects_non_positive_radius(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        branch = self._create_branch(client, headers)
        resp = client.post(
            f"/api/v1/vendors/me/branches/{branch['id']}/zones",
            headers=headers,
            json={"name": "Bad zone", "center_latitude": 40.7128, "center_longitude": -74.0060, "radius_meters": 0},
        )
        assert resp.status_code == 422

    def test_vendor_cannot_create_zone_on_another_vendors_branch(self, client, vendor, vendor2, login_as):
        headers1 = login_as(client, "vendor@example.com")
        branch = self._create_branch(client, headers1)

        headers2 = login_as(client, "vendor2@example.com")
        resp = client.post(
            f"/api/v1/vendors/me/branches/{branch['id']}/zones",
            headers=headers2,
            json={"name": "Sneaky zone", "center_latitude": 40.7128, "center_longitude": -74.0060, "radius_meters": 1000},
        )
        assert resp.status_code == 404

    def test_vendor_can_update_and_deactivate_zone(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        branch = self._create_branch(client, headers)
        zone = client.post(
            f"/api/v1/vendors/me/branches/{branch['id']}/zones",
            headers=headers,
            json={"name": "Zone", "center_latitude": 40.7128, "center_longitude": -74.0060, "radius_meters": 5000},
        ).get_json()["data"]["delivery_zone"]

        resp = client.patch(
            f"/api/v1/vendors/me/branches/{branch['id']}/zones/{zone['id']}",
            headers=headers,
            json={"status": "INACTIVE"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["delivery_zone"]["status"] == "INACTIVE"

    def test_vendor_can_delete_own_zone(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        branch = self._create_branch(client, headers)
        zone = client.post(
            f"/api/v1/vendors/me/branches/{branch['id']}/zones",
            headers=headers,
            json={"name": "Zone", "center_latitude": 40.7128, "center_longitude": -74.0060, "radius_meters": 5000},
        ).get_json()["data"]["delivery_zone"]

        resp = client.delete(
            f"/api/v1/vendors/me/branches/{branch['id']}/zones/{zone['id']}", headers=headers
        )
        assert resp.status_code == 200
        list_resp = client.get(f"/api/v1/vendors/me/branches/{branch['id']}/zones", headers=headers)
        assert list_resp.get_json()["data"]["delivery_zones"] == []
