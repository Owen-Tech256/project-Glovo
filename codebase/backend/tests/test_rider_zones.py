from tests.logistics_fixtures import LogisticsFixtures


class TestRiderZones(LogisticsFixtures):
    def test_join_and_list_zone(self, client, vendor, rider, login_as):
        vheaders = login_as(client, "vendor@example.com")
        rheaders = login_as(client, "rider@example.com")
        _branch, zone, _product = self.setup_branch_with_zone(client, vheaders)

        resp = client.post("/api/v1/rider/zones", headers=rheaders, json={"zone_id": zone["id"]})
        assert resp.status_code == 201

        listing = client.get("/api/v1/rider/zones", headers=rheaders).get_json()["data"]["zones"]
        assert len(listing) == 1
        assert listing[0]["zone_id"] == zone["id"]
        assert listing[0]["status"] == "ACTIVE"

    def test_joining_twice_is_idempotent(self, client, vendor, rider, login_as):
        vheaders = login_as(client, "vendor@example.com")
        rheaders = login_as(client, "rider@example.com")
        _branch, zone, _product = self.setup_branch_with_zone(client, vheaders)

        client.post("/api/v1/rider/zones", headers=rheaders, json={"zone_id": zone["id"]})
        client.post("/api/v1/rider/zones", headers=rheaders, json={"zone_id": zone["id"]})

        listing = client.get("/api/v1/rider/zones", headers=rheaders).get_json()["data"]["zones"]
        assert len(listing) == 1

    def test_join_nonexistent_zone_404s(self, client, rider, login_as):
        rheaders = login_as(client, "rider@example.com")
        resp = client.post("/api/v1/rider/zones", headers=rheaders, json={"zone_id": "does-not-exist"})
        assert resp.status_code == 404

    def test_leave_zone(self, client, vendor, rider, login_as):
        vheaders = login_as(client, "vendor@example.com")
        rheaders = login_as(client, "rider@example.com")
        _branch, zone, _product = self.setup_branch_with_zone(client, vheaders)
        client.post("/api/v1/rider/zones", headers=rheaders, json={"zone_id": zone["id"]})

        resp = client.delete(f"/api/v1/rider/zones/{zone['id']}", headers=rheaders)
        assert resp.status_code == 200

        listing = client.get("/api/v1/rider/zones", headers=rheaders).get_json()["data"]["zones"]
        assert listing == []

    def test_leave_zone_never_joined_404s(self, client, vendor, rider, login_as):
        vheaders = login_as(client, "vendor@example.com")
        rheaders = login_as(client, "rider@example.com")
        _branch, zone, _product = self.setup_branch_with_zone(client, vheaders)

        resp = client.delete(f"/api/v1/rider/zones/{zone['id']}", headers=rheaders)
        assert resp.status_code == 404

    def test_rejoin_after_leaving_reactivates(self, client, vendor, rider, login_as):
        vheaders = login_as(client, "vendor@example.com")
        rheaders = login_as(client, "rider@example.com")
        _branch, zone, _product = self.setup_branch_with_zone(client, vheaders)
        client.post("/api/v1/rider/zones", headers=rheaders, json={"zone_id": zone["id"]})
        client.delete(f"/api/v1/rider/zones/{zone['id']}", headers=rheaders)

        resp = client.post("/api/v1/rider/zones", headers=rheaders, json={"zone_id": zone["id"]})
        assert resp.status_code in (200, 201)
        listing = client.get("/api/v1/rider/zones", headers=rheaders).get_json()["data"]["zones"]
        assert len(listing) == 1
