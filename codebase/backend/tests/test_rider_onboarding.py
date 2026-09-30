from tests.logistics_fixtures import LogisticsFixtures


class TestRiderProfileProvisioning(LogisticsFixtures):
    def test_rider_profile_is_auto_provisioned_on_first_access(self, client, rider, login_as):
        headers = login_as(client, "rider@example.com")
        resp = client.get("/api/v1/rider/me", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()["data"]["rider"]
        assert data["onboarding_status"] == "PENDING"
        assert data["operational_status"] == "OFFLINE"
        assert data["vehicle"] is None

    def test_non_rider_cannot_access_rider_endpoints(self, client, customer, login_as):
        headers = login_as(client, "customer@example.com")
        resp = client.get("/api/v1/rider/me", headers=headers)
        assert resp.status_code == 403

    def test_unauthenticated_request_is_rejected(self, client):
        resp = client.get("/api/v1/rider/me")
        assert resp.status_code == 401


class TestRiderVehicleAndDocuments(LogisticsFixtures):
    def test_upsert_vehicle_profile(self, client, rider, login_as):
        headers = login_as(client, "rider@example.com")
        resp = client.patch(
            "/api/v1/rider/profile", headers=headers,
            json={"vehicle_type": "MOTORCYCLE", "registration_reference": "ABC-123"},
        )
        assert resp.status_code == 200
        vehicle = resp.get_json()["data"]["rider"]["vehicle"]
        assert vehicle["vehicle_type"] == "MOTORCYCLE"
        assert vehicle["registration_reference"] == "ABC-123"

    def test_upsert_vehicle_is_idempotent_update_not_duplicate(self, client, rider, login_as):
        headers = login_as(client, "rider@example.com")
        client.patch("/api/v1/rider/profile", headers=headers, json={"vehicle_type": "BICYCLE"})
        resp = client.patch(
            "/api/v1/rider/profile", headers=headers,
            json={"vehicle_type": "CAR", "registration_reference": "XYZ-999"},
        )
        vehicle = resp.get_json()["data"]["rider"]["vehicle"]
        assert vehicle["vehicle_type"] == "CAR"

    def test_rejects_invalid_vehicle_type(self, client, rider, login_as):
        headers = login_as(client, "rider@example.com")
        resp = client.patch("/api/v1/rider/profile", headers=headers, json={"vehicle_type": "SPACESHIP"})
        assert resp.status_code == 422

    def test_submit_and_list_documents(self, client, rider, login_as):
        headers = login_as(client, "rider@example.com")
        resp = client.post(
            "/api/v1/rider/documents", headers=headers,
            json={"document_type": "DRIVERS_LICENSE", "reference": "doc-ref-123", "expiry_date": "2030-01-01"},
        )
        assert resp.status_code == 201
        document = resp.get_json()["data"]["document"]
        assert document["verification_status"] == "PENDING"

        listing = client.get("/api/v1/rider/documents", headers=headers).get_json()["data"]["documents"]
        assert len(listing) == 1
        assert listing[0]["document_type"] == "DRIVERS_LICENSE"

    def test_rejects_invalid_document_type(self, client, rider, login_as):
        headers = login_as(client, "rider@example.com")
        resp = client.post(
            "/api/v1/rider/documents", headers=headers, json={"document_type": "PASSPORT", "reference": "x"}
        )
        assert resp.status_code == 422


class TestAdminRiderVerification(LogisticsFixtures):
    def test_admin_lists_riders(self, client, rider, admin, login_as):
        rheaders = login_as(client, "rider@example.com")
        client.get("/api/v1/rider/me", headers=rheaders)  # provisions the profile
        aheaders = login_as(client, "admin@example.com")

        resp = client.get("/api/v1/admin/riders", headers=aheaders)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["pagination"]["total"] == 1

    def test_admin_filters_riders_by_onboarding_status(self, client, rider, admin, login_as):
        rheaders = login_as(client, "rider@example.com")
        client.get("/api/v1/rider/me", headers=rheaders)
        aheaders = login_as(client, "admin@example.com")

        resp = client.get("/api/v1/admin/riders?status=APPROVED", headers=aheaders)
        assert resp.get_json()["data"]["pagination"]["total"] == 0

    def test_non_admin_cannot_list_riders(self, client, rider, login_as):
        headers = login_as(client, "rider@example.com")
        resp = client.get("/api/v1/admin/riders", headers=headers)
        assert resp.status_code == 403

    def test_full_approval_lifecycle(self, client, rider, admin, login_as):
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        rider_id = self.get_rider_id(client, rheaders)

        r1 = client.patch(f"/api/v1/admin/riders/{rider_id}/status", headers=aheaders, json={"status": "UNDER_REVIEW"})
        assert r1.get_json()["data"]["rider"]["onboarding_status"] == "UNDER_REVIEW"

        r2 = client.patch(
            f"/api/v1/admin/riders/{rider_id}/status", headers=aheaders,
            json={"status": "APPROVED", "reason": "Docs verified"},
        )
        assert r2.get_json()["data"]["rider"]["onboarding_status"] == "APPROVED"
        assert r2.get_json()["data"]["rider"]["approved_at"] is not None

    def test_cannot_skip_straight_to_approved(self, client, rider, admin, login_as):
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        rider_id = self.get_rider_id(client, rheaders)

        resp = client.patch(f"/api/v1/admin/riders/{rider_id}/status", headers=aheaders, json={"status": "APPROVED"})
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "INVALID_TRANSITION"

    def test_suspend_forces_rider_offline(self, client, rider, admin, login_as):
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        rider_id = self.approve_rider(client, aheaders, rheaders)
        client.patch("/api/v1/rider/availability", headers=rheaders, json={"status": "AVAILABLE"})

        resp = client.patch(f"/api/v1/admin/riders/{rider_id}/status", headers=aheaders, json={"status": "SUSPENDED"})
        assert resp.get_json()["data"]["rider"]["operational_status"] == "OFFLINE"

    def test_non_admin_cannot_change_rider_status(self, client, rider, vendor, login_as):
        rheaders = login_as(client, "rider@example.com")
        vheaders = login_as(client, "vendor@example.com")
        rider_id = self.get_rider_id(client, rheaders)

        resp = client.patch(f"/api/v1/admin/riders/{rider_id}/status", headers=vheaders, json={"status": "APPROVED"})
        assert resp.status_code == 403


class TestAdminDocumentReview(LogisticsFixtures):
    def test_admin_reviews_and_verifies_document(self, client, rider, admin, login_as):
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        rider_id = self.get_rider_id(client, rheaders)
        doc = client.post(
            "/api/v1/rider/documents", headers=rheaders,
            json={"document_type": "GOVERNMENT_ID", "reference": "gov-id-1"},
        ).get_json()["data"]["document"]

        resp = client.patch(
            f"/api/v1/admin/riders/{rider_id}/documents/{doc['id']}", headers=aheaders,
            json={"verification_status": "VERIFIED", "review_notes": "Looks good"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["document"]["verification_status"] == "VERIFIED"
        assert resp.get_json()["data"]["document"]["reviewed_by"] is not None

    def test_admin_rejects_document_with_notes(self, client, rider, admin, login_as):
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        rider_id = self.get_rider_id(client, rheaders)
        doc = client.post(
            "/api/v1/rider/documents", headers=rheaders,
            json={"document_type": "INSURANCE", "reference": "ins-1"},
        ).get_json()["data"]["document"]

        resp = client.patch(
            f"/api/v1/admin/riders/{rider_id}/documents/{doc['id']}", headers=aheaders,
            json={"verification_status": "REJECTED", "review_notes": "Expired"},
        )
        assert resp.get_json()["data"]["document"]["verification_status"] == "REJECTED"
        assert resp.get_json()["data"]["document"]["review_notes"] == "Expired"
