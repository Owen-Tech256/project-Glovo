from tests.support_fixtures import SupportFixtures


class _F(SupportFixtures):
    def _delivered_order(self, client, vheaders, cheaders, rheaders, aheaders):
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        return self.deliver_full_order(client, vheaders, cheaders, rheaders, aheaders, branch, zone, product)


class TestDisputeCreation(_F):
    def test_customer_can_open_dispute_on_own_order(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        order, _delivery = self._delivered_order(client, vheaders, cheaders, rheaders, aheaders)

        dispute = self.open_dispute(client, cheaders, order["id"], category="MISSING_ITEM", description="Fries missing.")
        assert dispute["dispute_number"].startswith("DSP-")
        assert dispute["status"] == "OPEN"
        assert dispute["order"]["id"] == order["id"]
        assert dispute["opened_by"]["role"] == "CUSTOMER"

    def test_vendor_can_open_dispute_on_own_order(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        order, _delivery = self._delivered_order(client, vheaders, cheaders, rheaders, aheaders)

        dispute = self.open_dispute(client, vheaders, order["id"], category="SERVICE_COMPLAINT", description="Rider was rude.")
        assert dispute["opened_by"]["role"] == "VENDOR"

    def test_stranger_cannot_open_dispute(self, client, vendor, customer, customer2, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        c2headers = login_as(client, "customer2@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        order, _delivery = self._delivered_order(client, vheaders, cheaders, rheaders, aheaders)

        resp = client.post(
            "/api/v1/disputes", headers=c2headers,
            json={"order_id": order["id"], "category": "OTHER", "description": "Not my order."},
        )
        assert resp.status_code == 403

    def test_dispute_from_ticket_links_them(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        order, _delivery = self._delivered_order(client, vheaders, cheaders, rheaders, aheaders)
        ticket = self.open_ticket(client, cheaders, category="ORDER_ISSUE")

        resp = client.post(
            "/api/v1/disputes", headers=cheaders,
            json={"order_id": order["id"], "category": "DAMAGED_ITEM", "description": "Box crushed.", "ticket_id": ticket["id"]},
        )
        assert resp.status_code == 201
        assert resp.get_json()["data"]["dispute"]["ticket_id"] == ticket["id"]

        # A ticket can only anchor one dispute.
        second = client.post(
            "/api/v1/disputes", headers=cheaders,
            json={"order_id": order["id"], "category": "OTHER", "description": "Again.", "ticket_id": ticket["id"]},
        )
        assert second.status_code == 422
        assert second.get_json()["error"]["code"] == "TICKET_ALREADY_DISPUTED"


class TestDisputeOwnerView(_F):
    def test_customer_lists_only_their_disputes(self, client, vendor, customer, customer2, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        c2headers = login_as(client, "customer2@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        order, _d = self._delivered_order(client, vheaders, cheaders, rheaders, aheaders)
        self.open_dispute(client, cheaders, order["id"])

        mine = client.get("/api/v1/disputes", headers=cheaders).get_json()["data"]["disputes"]
        theirs = client.get("/api/v1/disputes", headers=c2headers).get_json()["data"]["disputes"]
        assert len(mine) == 1
        assert len(theirs) == 0

    def test_can_add_evidence(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        order, _d = self._delivered_order(client, vheaders, cheaders, rheaders, aheaders)
        dispute = self.open_dispute(client, cheaders, order["id"])

        resp = client.post(
            f"/api/v1/disputes/{dispute['id']}/evidence", headers=cheaders,
            json={"evidence_type": "PHOTO", "secure_reference": "s3://bucket/photo.jpg"},
        )
        assert resp.status_code == 201

        detail = client.get(f"/api/v1/disputes/{dispute['id']}", headers=cheaders).get_json()["data"]["dispute"]
        assert len(detail["evidence"]) == 1


class TestDisputeInvestigation(_F):
    def test_moderator_cannot_access_disputes(self, client, moderator, login_as):
        mheaders = login_as(client, "moderator@example.com")
        resp = client.get("/api/v1/admin/disputes", headers=mheaders)
        assert resp.status_code == 403

    def test_operations_admin_can_investigate_non_financially(self, client, vendor, customer, rider, admin,
                                                                operations_admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        oheaders = login_as(client, "ops@example.com")
        order, _d = self._delivered_order(client, vheaders, cheaders, rheaders, aheaders)
        dispute = self.open_dispute(client, cheaders, order["id"])

        listing = client.get("/api/v1/admin/disputes", headers=oheaders)
        assert listing.status_code == 200

        note = client.post(
            f"/api/v1/admin/disputes/{dispute['id']}/actions", headers=oheaders,
            json={"action_type": "NOTE", "reason": "Checking with vendor."},
        )
        assert note.status_code == 201
        assert note.get_json()["data"]["action"]["action_type"] == "NOTE"

        detail = client.get(f"/api/v1/admin/disputes/{dispute['id']}", headers=oheaders).get_json()["data"]["dispute"]
        assert detail["status"] == "INVESTIGATING"
        assert len(detail["actions"]) == 1

    def test_operations_admin_cannot_resolve_with_refund(self, client, vendor, customer, rider, admin,
                                                           operations_admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        oheaders = login_as(client, "ops@example.com")
        order, _d = self._delivered_order(client, vheaders, cheaders, rheaders, aheaders)
        dispute = self.open_dispute(client, cheaders, order["id"])

        resp = client.post(
            f"/api/v1/admin/disputes/{dispute['id']}/resolve-with-refund", headers=oheaders,
            json={"reason": "Refunding for missing item."},
        )
        assert resp.status_code == 403

    def test_finance_admin_can_resolve_with_full_refund(self, client, vendor, customer, rider, admin,
                                                          finance_admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        fheaders = login_as(client, "financeadmin@example.com")
        order, _d = self._delivered_order(client, vheaders, cheaders, rheaders, aheaders)
        dispute = self.open_dispute(client, cheaders, order["id"], category="MISSING_ITEM")

        resp = client.post(
            f"/api/v1/admin/disputes/{dispute['id']}/resolve-with-refund", headers=fheaders,
            json={"reason": "Confirmed missing item."},
        )
        assert resp.status_code == 200
        body = resp.get_json()["data"]
        assert body["dispute"]["status"] == "RESOLVED"
        assert body["action"]["action_type"] == "REFUND_ISSUED"
        assert body["action"]["status"] == "COMPLETED"

        # The refund really went through Phase 5's refund service.
        refund_check = client.get(f"/api/v1/orders/{order['id']}/refunds", headers=cheaders)
        assert refund_check.status_code == 200
        refunds = refund_check.get_json()["data"]["refunds"]
        assert any(r["status"] == "SUCCEEDED" for r in refunds)

    def test_finance_admin_can_resolve_with_partial_refund(self, client, vendor, customer, rider, admin,
                                                             finance_admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        fheaders = login_as(client, "financeadmin@example.com")
        order, _d = self._delivered_order(client, vheaders, cheaders, rheaders, aheaders)
        dispute = self.open_dispute(client, cheaders, order["id"], category="DAMAGED_ITEM")

        resp = client.post(
            f"/api/v1/admin/disputes/{dispute['id']}/resolve-with-refund", headers=fheaders,
            json={"amount": "1.00", "reason": "Partial credit for damaged item."},
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["action"]["action_type"] == "PARTIAL_REFUND_ISSUED"

    def test_audit_trail_records_the_resolution(self, client, vendor, customer, rider, admin,
                                                 finance_admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        fheaders = login_as(client, "financeadmin@example.com")
        order, _d = self._delivered_order(client, vheaders, cheaders, rheaders, aheaders)
        dispute = self.open_dispute(client, cheaders, order["id"])
        client.post(f"/api/v1/admin/disputes/{dispute['id']}/resolve-with-refund", headers=fheaders, json={"reason": "ok"})

        events = client.get(
            "/api/v1/admin/audit/events", headers=aheaders,
            query_string={"entity_type": "DISPUTE", "entity_id": dispute["id"]},
        ).get_json()["data"]["events"]
        actions = [e["action"] for e in events]
        assert "DISPUTE_RESOLVED_WITH_REFUND" in actions
