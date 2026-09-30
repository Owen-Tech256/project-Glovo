from app.catalog.geo import haversine_distance_meters


class TestHaversineDistance:
    def test_same_point_is_zero_distance(self):
        assert haversine_distance_meters(40.7128, -74.0060, 40.7128, -74.0060) == 0

    def test_known_distance_new_york_to_los_angeles(self):
        # NYC to LA is ~3936 km great-circle distance.
        distance_km = haversine_distance_meters(40.7128, -74.0060, 34.0522, -118.2437) / 1000
        assert 3900 <= distance_km <= 3970

    def test_short_distance_is_reasonable(self):
        # Two points roughly 1km apart (about 0.009 degrees of latitude).
        distance = haversine_distance_meters(40.7128, -74.0060, 40.7218, -74.0060)
        assert 950 <= distance <= 1050


class TestDiscovery:
    def _setup_branch(self, client, headers, lat, lng, radius_meters, vendor_name=None, branch_name="Branch"):
        if vendor_name:
            client.patch("/api/v1/vendors/me", headers=headers, json={"name": vendor_name})
        branch = client.post(
            "/api/v1/vendors/me/branches",
            headers=headers,
            json={"name": branch_name, "address": "1 Main St", "latitude": lat, "longitude": lng},
        ).get_json()["data"]["branch"]
        client.post(
            f"/api/v1/vendors/me/branches/{branch['id']}/zones",
            headers=headers,
            json={"name": "zone", "center_latitude": lat, "center_longitude": lng, "radius_meters": radius_meters},
        )
        return branch

    def test_discovery_requires_lat_lng(self, client):
        resp = client.get("/api/v1/discovery/branches")
        assert resp.status_code == 422

    def test_discovery_finds_branch_within_zone(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        self._setup_branch(client, headers, 40.7128, -74.0060, 5000)

        resp = client.get("/api/v1/discovery/branches?lat=40.7128&lng=-74.0060")
        assert resp.status_code == 200
        assert len(resp.get_json()["data"]["branches"]) == 1

    def test_discovery_excludes_branch_outside_zone(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        self._setup_branch(client, headers, 40.7128, -74.0060, 1000)

        # ~40km away - well outside a 1km radius.
        resp = client.get("/api/v1/discovery/branches?lat=41.0000&lng=-74.0060")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["branches"] == []

    def test_discovery_excludes_inactive_zone(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        branch = self._setup_branch(client, headers, 40.7128, -74.0060, 5000)
        zones = client.get(
            f"/api/v1/vendors/me/branches/{branch['id']}/zones", headers=headers
        ).get_json()["data"]["delivery_zones"]
        client.patch(
            f"/api/v1/vendors/me/branches/{branch['id']}/zones/{zones[0]['id']}",
            headers=headers,
            json={"status": "INACTIVE"},
        )

        resp = client.get("/api/v1/discovery/branches?lat=40.7128&lng=-74.0060")
        assert resp.get_json()["data"]["branches"] == []

    def test_discovery_excludes_suspended_vendor(self, client, vendor, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        self._setup_branch(client, vheaders, 40.7128, -74.0060, 5000)
        me = client.get("/api/v1/vendors/me", headers=vheaders).get_json()["data"]["vendor"]

        aheaders = login_as(client, "admin@example.com")
        client.patch(f"/api/v1/admin/vendors/{me['id']}/status", headers=aheaders, json={"status": "SUSPENDED"})

        resp = client.get("/api/v1/discovery/branches?lat=40.7128&lng=-74.0060")
        assert resp.get_json()["data"]["branches"] == []

    def test_discovery_search_filters_by_name(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        self._setup_branch(client, headers, 40.7128, -74.0060, 5000, vendor_name="Pizza Palace")

        match = client.get("/api/v1/discovery/branches?lat=40.7128&lng=-74.0060&search=Pizza")
        assert len(match.get_json()["data"]["branches"]) == 1

        no_match = client.get("/api/v1/discovery/branches?lat=40.7128&lng=-74.0060&search=Sushi")
        assert no_match.get_json()["data"]["branches"] == []

    def test_discovery_rejects_unknown_sort(self, client):
        resp = client.get("/api/v1/discovery/branches?lat=40.7128&lng=-74.0060&sort=popularity")
        assert resp.status_code == 422

    def test_discovery_defaults_to_nearest_first(self, client, vendor, vendor2, login_as):
        headers = login_as(client, "vendor@example.com")
        headers2 = login_as(client, "vendor2@example.com")
        # Far branch first, near branch second - response order should
        # still come back nearest-first regardless of creation order.
        self._setup_branch(client, headers, 40.8000, -74.0060, 20000, branch_name="Far Branch")
        self._setup_branch(client, headers2, 40.7128, -74.0060, 5000, branch_name="Near Branch")

        resp = client.get("/api/v1/discovery/branches?lat=40.7128&lng=-74.0060")
        branches = resp.get_json()["data"]["branches"]
        assert [b["name"] for b in branches] == ["Near Branch", "Far Branch"]
        assert branches[0]["distance_meters"] < branches[1]["distance_meters"]

    def test_discovery_sort_by_name(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        self._setup_branch(client, headers, 40.7128, -74.0060, 5000, branch_name="Zebra Diner")
        self._setup_branch(client, headers, 40.7128, -74.0060, 5000, branch_name="Ace Diner")

        resp = client.get("/api/v1/discovery/branches?lat=40.7128&lng=-74.0060&sort=name")
        names = [b["name"] for b in resp.get_json()["data"]["branches"]]
        assert names == ["Ace Diner", "Zebra Diner"]

    def test_discovery_sort_by_rating_puts_unrated_last(self, client, vendor, vendor2, login_as, db):
        from app.models.vendor import Vendor

        headers = login_as(client, "vendor@example.com")
        headers2 = login_as(client, "vendor2@example.com")
        self._setup_branch(client, headers, 40.7128, -74.0060, 5000, branch_name="Unrated Diner")
        self._setup_branch(client, headers2, 40.7128, -74.0060, 5000, branch_name="Loved Diner")

        loved = Vendor.query.filter_by(user_id=vendor2.id).first()
        loved.rating_average = 4.8
        loved.rating_count = 12
        db.session.commit()

        resp = client.get("/api/v1/discovery/branches?lat=40.7128&lng=-74.0060&sort=rating")
        branches = resp.get_json()["data"]["branches"]
        assert [b["name"] for b in branches] == ["Loved Diner", "Unrated Diner"]
        assert branches[0]["vendor_rating_average"] == 4.8
        assert branches[1]["vendor_rating_average"] is None

    def test_discovery_min_rating_excludes_unrated_and_low_rated(self, client, vendor, vendor2, login_as, db):
        from app.models.vendor import Vendor

        headers = login_as(client, "vendor@example.com")
        headers2 = login_as(client, "vendor2@example.com")
        self._setup_branch(client, headers, 40.7128, -74.0060, 5000, branch_name="Unrated Diner")
        self._setup_branch(client, headers2, 40.7128, -74.0060, 5000, branch_name="Loved Diner")

        loved = Vendor.query.filter_by(user_id=vendor2.id).first()
        loved.rating_average = 4.8
        db.session.commit()

        resp = client.get("/api/v1/discovery/branches?lat=40.7128&lng=-74.0060&min_rating=4")
        names = [b["name"] for b in resp.get_json()["data"]["branches"]]
        assert names == ["Loved Diner"]

    def test_discovery_rejects_out_of_range_min_rating(self, client):
        resp = client.get("/api/v1/discovery/branches?lat=40.7128&lng=-74.0060&min_rating=6")
        assert resp.status_code == 422

    def test_discovery_paginates_results(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        self._setup_branch(client, headers, 40.7128, -74.0060, 5000, branch_name="Branch A")
        self._setup_branch(client, headers, 40.7128, -74.0060, 5000, branch_name="Branch B")

        page1 = client.get("/api/v1/discovery/branches?lat=40.7128&lng=-74.0060&sort=name&per_page=1&page=1")
        data1 = page1.get_json()["data"]
        assert len(data1["branches"]) == 1
        assert data1["branches"][0]["name"] == "Branch A"
        assert data1["pagination"] == {"page": 1, "per_page": 1, "total": 2, "total_pages": 2}

        page2 = client.get("/api/v1/discovery/branches?lat=40.7128&lng=-74.0060&sort=name&per_page=1&page=2")
        assert page2.get_json()["data"]["branches"][0]["name"] == "Branch B"

    def test_discovery_page_past_the_end_returns_empty(self, client, vendor, login_as):
        headers = login_as(client, "vendor@example.com")
        self._setup_branch(client, headers, 40.7128, -74.0060, 5000)

        resp = client.get("/api/v1/discovery/branches?lat=40.7128&lng=-74.0060&page=5")
        assert resp.get_json()["data"]["branches"] == []
