def register_payload(**overrides):
    payload = {
        "full_name": "Jane Doe",
        "email": "jane@example.com",
        "phone": "+15551234567",
        "password": "SecurePass123",
        "password_confirmation": "SecurePass123",
    }
    payload.update(overrides)
    return payload


class TestRegistration:
    def test_customer_registration_succeeds(self, client):
        resp = client.post("/api/v1/auth/register", json=register_payload())
        body = resp.get_json()

        assert resp.status_code == 201
        assert body["success"] is True
        assert body["data"]["user"]["role"] == "CUSTOMER"
        assert body["data"]["user"]["email"] == "jane@example.com"
        assert "password" not in body["data"]["user"]
        assert "password_hash" not in body["data"]["user"]
        assert "access_token" in body["data"]
        assert "refresh_token" in body["data"]

    def test_vendor_and_rider_can_self_register(self, client):
        vendor_resp = client.post("/api/v1/auth/register", json=register_payload(
            email="vendor@example.com", phone="+15551110001", role="VENDOR"
        ))
        rider_resp = client.post("/api/v1/auth/register", json=register_payload(
            email="rider@example.com", phone="+15551110002", role="RIDER"
        ))

        assert vendor_resp.get_json()["data"]["user"]["role"] == "VENDOR"
        assert rider_resp.get_json()["data"]["user"]["role"] == "RIDER"

    def test_admin_role_cannot_self_register(self, client):
        resp = client.post("/api/v1/auth/register", json=register_payload(role="ADMIN"))
        assert resp.status_code == 422
        assert resp.get_json()["success"] is False

    def test_duplicate_email_is_rejected(self, client):
        client.post("/api/v1/auth/register", json=register_payload())
        resp = client.post("/api/v1/auth/register", json=register_payload(phone="+15559999999"))

        body = resp.get_json()
        assert resp.status_code == 409
        assert body["error"]["code"] == "EMAIL_TAKEN"

    def test_duplicate_phone_is_rejected(self, client):
        client.post("/api/v1/auth/register", json=register_payload())
        resp = client.post("/api/v1/auth/register", json=register_payload(email="other@example.com"))

        body = resp.get_json()
        assert resp.status_code == 409
        assert body["error"]["code"] == "PHONE_TAKEN"

    def test_weak_password_is_rejected(self, client):
        resp = client.post("/api/v1/auth/register", json=register_payload(
            password="short", password_confirmation="short"
        ))
        assert resp.status_code == 422

    def test_mismatched_password_confirmation_is_rejected(self, client):
        resp = client.post("/api/v1/auth/register", json=register_payload(
            password_confirmation="SomethingElse123"
        ))
        assert resp.status_code == 422

    def test_invalid_email_is_rejected(self, client):
        resp = client.post("/api/v1/auth/register", json=register_payload(email="not-an-email"))
        assert resp.status_code == 422

    def test_password_hash_never_stored_in_plaintext(self, client, db):
        client.post("/api/v1/auth/register", json=register_payload())
        from app.models.user import User

        user = User.query.filter_by(email="jane@example.com").first()
        assert user.password_hash != "SecurePass123"
        assert user.password_hash.startswith("$2b$")
