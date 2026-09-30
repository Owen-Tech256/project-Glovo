class TestPasswordReset:
    def test_forgot_password_for_existing_account_returns_generic_message(self, client, customer):
        resp = client.post("/api/v1/auth/forgot-password", json={"email": "customer@example.com"})
        body = resp.get_json()
        assert resp.status_code == 200
        assert body["success"] is True
        # In TESTING config the raw token is surfaced so the flow can be
        # exercised end-to-end without a real mail server.
        assert "debug_reset_token" in body["data"]

    def test_forgot_password_for_unknown_email_returns_same_generic_message(self, client):
        """Must not disclose whether the account exists."""
        resp = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
        body = resp.get_json()
        assert resp.status_code == 200
        assert body["message"] == "If an account with that email exists, a password reset link has been sent."
        assert body["data"].get("debug_reset_token") is None

    def test_forgot_password_invalid_email_format_is_validation_error(self, client):
        resp = client.post("/api/v1/auth/forgot-password", json={"email": "not-an-email"})
        assert resp.status_code == 422

    def test_full_reset_flow_allows_login_with_new_password(self, client, customer):
        forgot_resp = client.post("/api/v1/auth/forgot-password", json={"email": "customer@example.com"})
        token = forgot_resp.get_json()["data"]["debug_reset_token"]

        reset_resp = client.post("/api/v1/auth/reset-password", json={
            "token": token,
            "password": "BrandNewPass123",
            "password_confirmation": "BrandNewPass123",
        })
        assert reset_resp.status_code == 200

        old_login = client.post("/api/v1/auth/login", json={
            "identifier": "customer@example.com", "password": "Password123"
        })
        assert old_login.status_code == 401

        new_login = client.post("/api/v1/auth/login", json={
            "identifier": "customer@example.com", "password": "BrandNewPass123"
        })
        assert new_login.status_code == 200

    def test_reset_token_cannot_be_reused(self, client, customer):
        forgot_resp = client.post("/api/v1/auth/forgot-password", json={"email": "customer@example.com"})
        token = forgot_resp.get_json()["data"]["debug_reset_token"]

        first = client.post("/api/v1/auth/reset-password", json={
            "token": token, "password": "FirstNewPass123", "password_confirmation": "FirstNewPass123",
        })
        second = client.post("/api/v1/auth/reset-password", json={
            "token": token, "password": "SecondNewPass123", "password_confirmation": "SecondNewPass123",
        })
        assert first.status_code == 200
        assert second.status_code == 422
        assert second.get_json()["error"]["code"] == "INVALID_RESET_TOKEN"

    def test_reset_with_garbage_token_fails(self, client):
        resp = client.post("/api/v1/auth/reset-password", json={
            "token": "not-a-real-token", "password": "SomePass123", "password_confirmation": "SomePass123",
        })
        assert resp.status_code == 422

    def test_reset_password_mismatched_confirmation_fails(self, client, customer):
        forgot_resp = client.post("/api/v1/auth/forgot-password", json={"email": "customer@example.com"})
        token = forgot_resp.get_json()["data"]["debug_reset_token"]

        resp = client.post("/api/v1/auth/reset-password", json={
            "token": token, "password": "SomePass123", "password_confirmation": "Different123",
        })
        assert resp.status_code == 422

    def test_reset_password_revokes_existing_refresh_tokens(self, client, customer):
        login_resp = client.post("/api/v1/auth/login", json={
            "identifier": "customer@example.com", "password": "Password123"
        }).get_json()
        old_refresh_token = login_resp["data"]["refresh_token"]

        forgot_resp = client.post("/api/v1/auth/forgot-password", json={"email": "customer@example.com"})
        token = forgot_resp.get_json()["data"]["debug_reset_token"]
        client.post("/api/v1/auth/reset-password", json={
            "token": token, "password": "BrandNewPass123", "password_confirmation": "BrandNewPass123",
        })

        refresh_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh_token})
        assert refresh_resp.status_code == 401
