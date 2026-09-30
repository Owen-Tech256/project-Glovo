from app.models.user import UserRole, UserStatus


class TestLogin:
    def test_login_with_email_succeeds(self, client, customer):
        resp = client.post("/api/v1/auth/login", json={
            "identifier": "customer@example.com", "password": "Password123"
        })
        body = resp.get_json()
        assert resp.status_code == 200
        assert body["data"]["user"]["email"] == "customer@example.com"
        assert "access_token" in body["data"]
        assert "refresh_token" in body["data"]

    def test_login_with_phone_succeeds(self, client, customer):
        resp = client.post("/api/v1/auth/login", json={
            "identifier": "+10000000001", "password": "Password123"
        })
        assert resp.status_code == 200

    def test_login_wrong_password_fails(self, client, customer):
        resp = client.post("/api/v1/auth/login", json={
            "identifier": "customer@example.com", "password": "WrongPassword1"
        })
        body = resp.get_json()
        assert resp.status_code == 401
        assert body["error"]["code"] == "INVALID_CREDENTIALS"

    def test_login_unknown_identifier_fails_with_same_error_as_wrong_password(self, client, customer):
        """Ensures the API never discloses whether an account exists."""
        resp_unknown = client.post("/api/v1/auth/login", json={
            "identifier": "nobody@example.com", "password": "Password123"
        })
        resp_wrong_pw = client.post("/api/v1/auth/login", json={
            "identifier": "customer@example.com", "password": "WrongPassword1"
        })
        assert resp_unknown.status_code == resp_wrong_pw.status_code == 401
        assert resp_unknown.get_json()["error"]["code"] == resp_wrong_pw.get_json()["error"]["code"]

    def test_login_rejects_suspended_account(self, client, make_user):
        make_user(email="susp@example.com", phone="+19990000001", password="Password123",
                   role=UserRole.CUSTOMER, status=UserStatus.SUSPENDED)
        resp = client.post("/api/v1/auth/login", json={"identifier": "susp@example.com", "password": "Password123"})
        assert resp.status_code == 403
        assert resp.get_json()["error"]["code"] == "ACCOUNT_NOT_ACTIVE"

    def test_login_rejects_disabled_account(self, client, make_user):
        make_user(email="dis@example.com", phone="+19990000002", password="Password123",
                   role=UserRole.CUSTOMER, status=UserStatus.DISABLED)
        resp = client.post("/api/v1/auth/login", json={"identifier": "dis@example.com", "password": "Password123"})
        assert resp.status_code == 403

    def test_login_missing_fields_is_validation_error(self, client):
        resp = client.post("/api/v1/auth/login", json={"identifier": "x@example.com"})
        assert resp.status_code == 422


class TestMe:
    def test_me_requires_authentication(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_me_returns_current_user_profile(self, client, customer, login_as):
        headers = login_as(client, "customer@example.com")
        resp = client.get("/api/v1/auth/me", headers=headers)
        body = resp.get_json()
        assert resp.status_code == 200
        assert body["data"]["user"]["email"] == "customer@example.com"
        assert "password_hash" not in body["data"]["user"]

    def test_me_rejects_garbage_token(self, client):
        resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
        assert resp.status_code == 401


class TestLogout:
    def test_logout_revokes_refresh_token(self, client, customer):
        login_resp = client.post("/api/v1/auth/login", json={
            "identifier": "customer@example.com", "password": "Password123"
        }).get_json()
        access_token = login_resp["data"]["access_token"]
        refresh_token = login_resp["data"]["refresh_token"]

        logout_resp = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert logout_resp.status_code == 200

        # The revoked refresh token must no longer work.
        refresh_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert refresh_resp.status_code == 401

    def test_logout_requires_authentication(self, client):
        resp = client.post("/api/v1/auth/logout", json={"refresh_token": "whatever"})
        assert resp.status_code == 401


class TestRefresh:
    def test_refresh_issues_new_token_pair_and_rotates(self, client, customer):
        login_resp = client.post("/api/v1/auth/login", json={
            "identifier": "customer@example.com", "password": "Password123"
        }).get_json()
        old_refresh = login_resp["data"]["refresh_token"]

        refresh_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
        body = refresh_resp.get_json()
        assert refresh_resp.status_code == 200
        assert body["data"]["refresh_token"] != old_refresh

        # Old refresh token must be dead after rotation.
        replay_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
        assert replay_resp.status_code == 401

    def test_refresh_rejects_garbage_token(self, client):
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "garbage"})
        assert resp.status_code == 401
