from tests.logistics_fixtures import LogisticsFixtures


class TestAvailability(LogisticsFixtures):
    def test_cannot_go_available_before_approval(self, client, rider, login_as):
        headers = login_as(client, "rider@example.com")
        resp = client.patch("/api/v1/rider/availability", headers=headers, json={"status": "AVAILABLE"})
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "NOT_DISPATCH_ELIGIBLE"

    def test_can_go_available_once_approved(self, client, rider, admin, login_as):
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        self.approve_rider(client, aheaders, rheaders)

        resp = client.patch("/api/v1/rider/availability", headers=rheaders, json={"status": "AVAILABLE"})
        assert resp.status_code == 200
        assert resp.get_json()["data"]["rider"]["operational_status"] == "AVAILABLE"

    def test_cannot_manually_set_busy(self, client, rider, admin, login_as):
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        self.approve_rider(client, aheaders, rheaders)

        resp = client.patch("/api/v1/rider/availability", headers=rheaders, json={"status": "BUSY"})
        assert resp.status_code == 422

    def test_availability_change_recorded_with_reason(self, client, rider, admin, login_as):
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        self.approve_rider(client, aheaders, rheaders)
        client.patch(
            "/api/v1/rider/availability", headers=rheaders, json={"status": "AVAILABLE", "reason": "Starting shift"}
        )

        history = client.get("/api/v1/rider/availability", headers=rheaders).get_json()["data"]["history"]
        assert history[0]["to_status"] == "AVAILABLE"
        assert history[0]["reason"] == "Starting shift"
        assert history[0]["from_status"] == "OFFLINE"

    def test_cannot_go_offline_while_busy(self, client, db, rider, admin, login_as):
        from app.models.rider import Rider, RiderOperationalStatus

        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        self.approve_rider(client, aheaders, rheaders)
        client.patch("/api/v1/rider/availability", headers=rheaders, json={"status": "AVAILABLE"})

        db_rider = Rider.query.filter_by(user_id=rider.id).first()
        db_rider.operational_status = RiderOperationalStatus.BUSY
        db.session.commit()

        resp = client.patch("/api/v1/rider/availability", headers=rheaders, json={"status": "OFFLINE"})
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "RIDER_BUSY"


class TestLocation(LogisticsFixtures):
    def test_valid_location_update(self, client, rider, login_as):
        headers = login_as(client, "rider@example.com")
        resp = client.post("/api/v1/rider/location", headers=headers, json={"latitude": 40.7128, "longitude": -74.0060})
        assert resp.status_code == 200
        location = resp.get_json()["data"]["location"]
        assert location["latitude"] == 40.7128
        assert location["is_fresh"] is True

    def test_rejects_out_of_range_latitude(self, client, rider, login_as):
        headers = login_as(client, "rider@example.com")
        resp = client.post("/api/v1/rider/location", headers=headers, json={"latitude": 999, "longitude": -74.0060})
        assert resp.status_code == 422

    def test_rejects_out_of_range_longitude(self, client, rider, login_as):
        headers = login_as(client, "rider@example.com")
        resp = client.post("/api/v1/rider/location", headers=headers, json={"latitude": 40.7128, "longitude": -999})
        assert resp.status_code == 422

    def test_rejects_missing_coordinates(self, client, rider, login_as):
        headers = login_as(client, "rider@example.com")
        resp = client.post("/api/v1/rider/location", headers=headers, json={"latitude": 40.7128})
        assert resp.status_code == 422

    def test_rapid_repeated_updates_are_rate_limited(self, client, rider, login_as):
        headers = login_as(client, "rider@example.com")
        first = client.post("/api/v1/rider/location", headers=headers, json={"latitude": 40.7128, "longitude": -74.0060})
        assert first.status_code == 200

        second = client.post("/api/v1/rider/location", headers=headers, json={"latitude": 40.7129, "longitude": -74.0061})
        assert second.status_code == 429
        assert second.get_json()["error"]["code"] == "LOCATION_RATE_LIMITED"

    def test_update_after_interval_elapses_is_accepted(self, client, db, rider, login_as):
        from datetime import timedelta
        from app.models.rider import Rider
        from app.models.base import _utcnow

        headers = login_as(client, "rider@example.com")
        client.post("/api/v1/rider/location", headers=headers, json={"latitude": 40.7128, "longitude": -74.0060})

        db_rider = Rider.query.filter_by(user_id=rider.id).first()
        db_rider.location_updated_at = _utcnow() - timedelta(seconds=10)
        db.session.commit()

        resp = client.post("/api/v1/rider/location", headers=headers, json={"latitude": 40.7200, "longitude": -74.0100})
        assert resp.status_code == 200

    def test_stale_location_is_flagged(self, client, db, rider, login_as):
        from datetime import timedelta
        from app.models.rider import Rider
        from app.models.base import _utcnow

        headers = login_as(client, "rider@example.com")
        client.post("/api/v1/rider/location", headers=headers, json={"latitude": 40.7128, "longitude": -74.0060})

        db_rider = Rider.query.filter_by(user_id=rider.id).first()
        db_rider.location_updated_at = _utcnow() - timedelta(seconds=1000)
        db.session.commit()

        resp = client.get("/api/v1/rider/location", headers=headers)
        assert resp.get_json()["data"]["location"]["is_fresh"] is False
