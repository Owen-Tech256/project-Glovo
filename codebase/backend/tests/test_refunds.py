from tests.payments_fixtures import PaymentsFixtures


class _Fixtures(PaymentsFixtures):
    def _paid_order(self, client, vheaders, cheaders):
        branch, _zone, product = self.setup_branch_with_zone(client, vheaders)
        order = self.place_order(client, vheaders, cheaders, branch, product)  # already pays
        return order


class TestRefundRequest(_Fixtures):
    def test_customer_can_request_full_refund(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        order = self._paid_order(client, vheaders, cheaders)

        resp = client.post(
            f"/api/v1/orders/{order['id']}/refund-request", headers=cheaders, json={"reason": "Changed my mind"}
        )
        assert resp.status_code == 201
        refund = resp.get_json()["data"]["refund"]
        assert refund["amount"] == order["total"]
        # REFUND_REQUIRES_APPROVAL defaults to True - stays REQUESTED.
        assert refund["status"] == "REQUESTED"

    def test_customer_can_request_partial_refund(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        order = self._paid_order(client, vheaders, cheaders)

        resp = client.post(
            f"/api/v1/orders/{order['id']}/refund-request", headers=cheaders,
            json={"amount": "1.00", "reason": "One item was missing"},
        )
        assert resp.status_code == 201
        assert resp.get_json()["data"]["refund"]["amount"] == "1.00"

    def test_refund_amount_cannot_exceed_refundable(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        order = self._paid_order(client, vheaders, cheaders)

        resp = client.post(
            f"/api/v1/orders/{order['id']}/refund-request", headers=cheaders,
            json={"amount": "999.00", "reason": "Too much"},
        )
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "REFUND_EXCEEDS_REFUNDABLE"

    def test_cannot_refund_an_unpaid_order(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, _zone, product = self.setup_branch_with_zone(client, vheaders)
        order = self.place_unpaid_order(client, vheaders, cheaders, branch, product)

        resp = client.post(
            f"/api/v1/orders/{order['id']}/refund-request", headers=cheaders, json={"reason": "No payment yet"}
        )
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "NO_PAYMENT_TO_REFUND"

    def test_second_full_refund_request_is_rejected_once_first_is_committed(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        order = self._paid_order(client, vheaders, cheaders)

        first = client.post(
            f"/api/v1/orders/{order['id']}/refund-request", headers=cheaders, json={"reason": "First request"}
        )
        assert first.status_code == 201

        # The full refundable amount is already reserved by the first
        # REQUESTED refund (see refund_service module docstring) - a second
        # concurrent request for more than what's left must be rejected,
        # not silently double-committed.
        second = client.post(
            f"/api/v1/orders/{order['id']}/refund-request", headers=cheaders, json={"reason": "Second request"}
        )
        assert second.status_code == 422
        # Nothing is left reserved for a new request (the first REQUESTED
        # refund already committed the full refundable amount).
        assert second.get_json()["error"]["code"] == "NOTHING_TO_REFUND"

    def test_refund_idempotency_key_returns_same_refund(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        order = self._paid_order(client, vheaders, cheaders)

        payload = {"reason": "test", "idempotency_key": "refund-key-1"}
        first = client.post(f"/api/v1/orders/{order['id']}/refund-request", headers=cheaders, json=payload)
        second = client.post(f"/api/v1/orders/{order['id']}/refund-request", headers=cheaders, json=payload)
        assert second.status_code == 200
        assert first.get_json()["data"]["refund"]["id"] == second.get_json()["data"]["refund"]["id"]


class TestAdminRefundApproval(_Fixtures):
    def test_admin_can_approve_and_process_a_refund(self, client, vendor, customer, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        aheaders = login_as(client, "admin@example.com")
        order = self._paid_order(client, vheaders, cheaders)
        refund = client.post(
            f"/api/v1/orders/{order['id']}/refund-request", headers=cheaders, json={"reason": "test"}
        ).get_json()["data"]["refund"]

        resp = client.post(f"/api/v1/admin/refunds/{refund['id']}/approve", headers=aheaders)
        assert resp.status_code == 200
        approved = resp.get_json()["data"]["refund"]
        assert approved["status"] == "SUCCEEDED"
        assert approved["provider_reference"] is not None

        payment = client.get(f"/api/v1/orders/{order['id']}/payments", headers=cheaders).get_json()["data"]["payments"][0]
        assert payment["status"] == "REFUNDED"

    def test_admin_can_reject_a_refund(self, client, vendor, customer, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        aheaders = login_as(client, "admin@example.com")
        order = self._paid_order(client, vheaders, cheaders)
        refund = client.post(
            f"/api/v1/orders/{order['id']}/refund-request", headers=cheaders, json={"reason": "test"}
        ).get_json()["data"]["refund"]

        resp = client.post(
            f"/api/v1/admin/refunds/{refund['id']}/reject", headers=aheaders, json={"reason": "Not eligible"}
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["refund"]["status"] == "REJECTED"

        # A rejected refund releases its reservation - a new request for
        # the full amount should now succeed.
        second = client.post(
            f"/api/v1/orders/{order['id']}/refund-request", headers=cheaders, json={"reason": "Retry"}
        )
        assert second.status_code == 201

    def test_declined_refund_can_be_retried_by_admin(self, client, vendor, customer, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        aheaders = login_as(client, "admin@example.com")
        order = self._paid_order(client, vheaders, cheaders)
        refund = client.post(
            f"/api/v1/orders/{order['id']}/refund-request", headers=cheaders,
            json={"reason": "MOCK_FAIL please decline this refund"},
        ).get_json()["data"]["refund"]

        approved = client.post(f"/api/v1/admin/refunds/{refund['id']}/approve", headers=aheaders).get_json()["data"]["refund"]
        assert approved["status"] == "FAILED"

        retried = client.post(f"/api/v1/admin/refunds/{refund['id']}/retry", headers=aheaders)
        assert retried.status_code == 200
        # Still declined (same reason text triggers MOCK_FAIL again) -
        # what matters is retry is a safe, repeatable operation.
        assert retried.get_json()["data"]["refund"]["status"] == "FAILED"

    def test_non_admin_cannot_approve_refunds(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        order = self._paid_order(client, vheaders, cheaders)
        refund = client.post(
            f"/api/v1/orders/{order['id']}/refund-request", headers=cheaders, json={"reason": "test"}
        ).get_json()["data"]["refund"]

        resp = client.post(f"/api/v1/admin/refunds/{refund['id']}/approve", headers=cheaders)
        assert resp.status_code == 403


class TestRefundAutoApprove:
    def test_refund_auto_approves_and_processes_when_not_requiring_approval(self, client, vendor, customer, login_as, app):
        app.config["REFUND_REQUIRES_APPROVAL"] = False
        fixtures = PaymentsFixtures()
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, _zone, product = fixtures.setup_branch_with_zone(client, vheaders)
        order = fixtures.place_order(client, vheaders, cheaders, branch, product)

        resp = client.post(
            f"/api/v1/orders/{order['id']}/refund-request", headers=cheaders, json={"reason": "test"}
        )
        assert resp.status_code == 201
        assert resp.get_json()["data"]["refund"]["status"] == "SUCCEEDED"
