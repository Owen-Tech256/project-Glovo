from app.extensions import bcrypt


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = bcrypt.generate_hash("MyPassword123")
        assert hashed != "MyPassword123"

    def test_verify_succeeds_for_correct_password(self):
        hashed = bcrypt.generate_hash("MyPassword123")
        assert bcrypt.verify("MyPassword123", hashed) is True

    def test_verify_fails_for_incorrect_password(self):
        hashed = bcrypt.generate_hash("MyPassword123")
        assert bcrypt.verify("WrongPassword", hashed) is False

    def test_two_hashes_of_same_password_differ(self):
        """Confirms a random salt is used each time."""
        hash_one = bcrypt.generate_hash("MyPassword123")
        hash_two = bcrypt.generate_hash("MyPassword123")
        assert hash_one != hash_two

    def test_verify_handles_garbage_hash_gracefully(self):
        assert bcrypt.verify("anything", "not-a-real-hash") is False


class TestApiErrorFormat:
    def test_validation_error_has_standard_shape(self, client):
        resp = client.post("/api/v1/auth/register", json={})
        body = resp.get_json()
        assert resp.status_code == 422
        assert body["success"] is False
        assert "code" in body["error"]
        assert "message" in body["error"]

    def test_404_has_standard_shape(self, client):
        resp = client.get("/api/v1/this-route-does-not-exist")
        body = resp.get_json()
        assert resp.status_code == 404
        assert body["success"] is False
        assert body["error"]["code"] == "NOT_FOUND"

    def test_success_response_has_standard_shape(self, client):
        resp = client.get("/api/v1/health")
        body = resp.get_json()
        assert resp.status_code == 200
        assert body["success"] is True
        assert "message" in body
        assert "data" in body

    def test_no_internal_exception_details_leak_in_production_mode(self, client, app, monkeypatch):
        app.config["DEBUG"] = False
        # Force an unexpected error path and confirm the response is generic.
        resp = client.post("/api/v1/auth/login", data="not-json", content_type="application/json")
        assert resp.status_code in (400, 422, 500)
        body = resp.get_json()
        assert body["success"] is False
        assert "Traceback" not in str(body)
