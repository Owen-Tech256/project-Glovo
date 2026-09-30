import hashlib
import hmac
import json

from tests.payments_fixtures import PaymentsFixtures

WEBHOOK_SECRET = b"dev-webhook-secret-change-me"


def _sign(payload: dict) -> bytes:
    raw_body = json.dumps(payload, sort_keys=True).encode("utf-8")
    signature = hmac.new(WEBHOOK_SECRET, raw_body, hashlib.sha256).hexdigest()
    return raw_body, signature


class _Fixtures(PaymentsFixtures):
    def _setup(self, client, vheaders, cheaders):
        branch, _zone, product = self.setup_branch_with_zone(client, vheaders)
        order = self.place_unpaid_order(client, vheaders, cheaders, branch, product)
        return order


class TestPaymentCreation(_Fixtures):
    def test_customer_can_pay_for_order(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        order = self._setup(client, vheaders, cheaders)
        assert order["status"] == "PENDING_PAYMENT"

        resp = client.post("/api/v1/payments", headers=cheaders, json={"order_id": order["id"]})
        assert resp.status_code == 201
        payment = resp.get_json()["data"]["payment"]
        assert payment["status"] == "SUCCEEDED"
        assert payment["amount"] == order["total"]
        assert payment["order_id"] == order["id"]

        refreshed = client.get(f"/api/v1/orders/{order['id']}", headers=cheaders).get_json()["data"]["order"]
        assert refreshed["status"] == "PAYMENT_CONFIRMED"

    def test_payment_amount_is_server_calculated_never_client_supplied(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        order = self._setup(client, vheaders, cheaders)

        # The schema doesn't even accept an amount field - any extra field
        # sent is silently dropped (Meta.unknown = "exclude").
        resp = client.post(
            "/api/v1/payments", headers=cheaders, json={"order_id": order["id"], "amount": "0.01"}
        )
        payment = resp.get_json()["data"]["payment"]
        assert payment["amount"] == order["total"]
        assert payment["amount"] != "0.01"

    def test_cannot_pay_for_order_twice(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        order = self._setup(client, vheaders, cheaders)
        client.post("/api/v1/payments", headers=cheaders, json={"order_id": order["id"]})

        resp = client.post("/api/v1/payments", headers=cheaders, json={"order_id": order["id"]})
        assert resp.status_code == 409
        assert resp.get_json()["error"]["code"] == "ORDER_ALREADY_PAID"

    def test_cannot_pay_for_someone_elses_order(self, client, vendor, customer, customer2, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        order = self._setup(client, vheaders, cheaders)

        c2headers = login_as(client, "customer2@example.com")
        resp = client.post("/api/v1/payments", headers=c2headers, json={"order_id": order["id"]})
        assert resp.status_code == 404

    def test_payment_idempotency_key_returns_same_payment(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        order = self._setup(client, vheaders, cheaders)

        payload = {"order_id": order["id"], "idempotency_key": "pay-key-1"}
        first = client.post("/api/v1/payments", headers=cheaders, json=payload)
        assert first.status_code == 201
        second = client.post("/api/v1/payments", headers=cheaders, json=payload)
        assert second.status_code == 200
        assert first.get_json()["data"]["payment"]["id"] == second.get_json()["data"]["payment"]["id"]

    def test_declined_card_leaves_order_pending_payment_and_can_retry(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        order = self._setup(client, vheaders, cheaders)

        declined = client.post(
            "/api/v1/payments", headers=cheaders, json={"order_id": order["id"], "method": "MOCK_DECLINE"}
        )
        assert declined.status_code == 201
        assert declined.get_json()["data"]["payment"]["status"] == "FAILED"

        refreshed = client.get(f"/api/v1/orders/{order['id']}", headers=cheaders).get_json()["data"]["order"]
        assert refreshed["status"] == "PENDING_PAYMENT"

        retry = client.post("/api/v1/payments", headers=cheaders, json={"order_id": order["id"]})
        assert retry.status_code == 201
        assert retry.get_json()["data"]["payment"]["status"] == "SUCCEEDED"

        refreshed = client.get(f"/api/v1/orders/{order['id']}", headers=cheaders).get_json()["data"]["order"]
        assert refreshed["status"] == "PAYMENT_CONFIRMED"


class TestPaymentVerifyAndLookup(_Fixtures):
    def test_verify_is_idempotent_on_already_succeeded_payment(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        order = self._setup(client, vheaders, cheaders)
        payment = client.post(
            "/api/v1/payments", headers=cheaders, json={"order_id": order["id"]}
        ).get_json()["data"]["payment"]

        resp = client.post(f"/api/v1/payments/{payment['id']}/verify", headers=cheaders)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["payment"]["status"] == "SUCCEEDED"

    def test_get_payment_and_list_order_payments(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        order = self._setup(client, vheaders, cheaders)
        payment = client.post(
            "/api/v1/payments", headers=cheaders, json={"order_id": order["id"]}
        ).get_json()["data"]["payment"]

        resp = client.get(f"/api/v1/payments/{payment['id']}", headers=cheaders)
        assert resp.status_code == 200

        listed = client.get(f"/api/v1/orders/{order['id']}/payments", headers=cheaders)
        assert listed.status_code == 200
        assert len(listed.get_json()["data"]["payments"]) == 1


class TestWebhooks(_Fixtures):
    def test_webhook_duplicate_delivery_is_harmless(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        order = self._setup(client, vheaders, cheaders)
        payment = client.post(
            "/api/v1/payments", headers=cheaders, json={"order_id": order["id"]}
        ).get_json()["data"]["payment"]

        payload = {
            "event_id": "evt_test_1",
            "event_type": "payment.succeeded",
            "provider_reference": payment["provider_reference"],
        }
        raw_body, signature = _sign(payload)

        first = client.post(
            "/api/v1/webhooks/payments/mock", data=raw_body, headers={"Content-Type": "application/json", "X-Signature": signature}
        )
        assert first.status_code == 200
        assert first.get_json()["data"]["status"] == "PROCESSED"

        second = client.post(
            "/api/v1/webhooks/payments/mock", data=raw_body, headers={"Content-Type": "application/json", "X-Signature": signature}
        )
        assert second.status_code == 200
        assert second.get_json()["data"]["status"] == "ALREADY_PROCESSED"

    def test_webhook_rejects_invalid_signature(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        order = self._setup(client, vheaders, cheaders)
        payment = client.post(
            "/api/v1/payments", headers=cheaders, json={"order_id": order["id"]}
        ).get_json()["data"]["payment"]

        payload = {
            "event_id": "evt_test_2",
            "event_type": "payment.succeeded",
            "provider_reference": payment["provider_reference"],
        }
        raw_body = json.dumps(payload, sort_keys=True).encode("utf-8")

        resp = client.post(
            "/api/v1/webhooks/payments/mock", data=raw_body,
            headers={"Content-Type": "application/json", "X-Signature": "not-a-real-signature"},
        )
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "INVALID_WEBHOOK"


class TestLedgerBalance(_Fixtures):
    def test_ledger_stays_balanced_after_a_payment(self, client, vendor, customer, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        order = self._setup(client, vheaders, cheaders)
        client.post("/api/v1/payments", headers=cheaders, json={"order_id": order["id"]})

        aheaders = login_as(client, "admin@example.com")
        resp = client.get("/api/v1/admin/reconciliation/summary", headers=aheaders)
        assert resp.status_code == 200
        summary = resp.get_json()["data"]
        assert summary["balanced"] is True
        assert summary["total_debits"] == summary["total_credits"]
