from tests.support_fixtures import SupportFixtures


class _F(SupportFixtures):
    pass


class TestTicketCreation(_F):
    def test_customer_can_create_ticket(self, client, customer, login_as):
        cheaders = login_as(client, "customer@example.com")
        ticket = self.open_ticket(client, cheaders, category="ACCOUNT_ISSUE", subject="Can't log in")
        assert ticket["ticket_number"].startswith("TCK-")
        assert ticket["status"] == "OPEN"
        assert ticket["priority"] == "NORMAL"
        assert ticket["requester"]["role"] == "CUSTOMER"

    def test_ticket_can_reference_own_order(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        order, _delivery = self.deliver_full_order(client, vheaders, cheaders, rheaders, aheaders, branch, zone, product)

        ticket = self.open_ticket(
            client, cheaders, category="ORDER_ISSUE", subject="Missing item",
            related_entity_type="ORDER", related_entity_id=order["id"],
        )
        assert ticket["related_entity_type"] == "ORDER"
        assert ticket["related_entity_id"] == order["id"]

    def test_cannot_reference_someone_elses_order(self, client, vendor, customer, customer2, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        c2headers = login_as(client, "customer2@example.com")
        branch, _zone, product = self.setup_branch_with_zone(client, vheaders)
        order = self.place_order(client, vheaders, cheaders, branch, product)

        resp = client.post(
            "/api/v1/support/tickets", headers=c2headers,
            json={"category": "ORDER_ISSUE", "subject": "Not mine", "message": "hi",
                  "related_entity_type": "ORDER", "related_entity_id": order["id"]},
        )
        assert resp.status_code == 403

    def test_invalid_category_rejected(self, client, customer, login_as):
        cheaders = login_as(client, "customer@example.com")
        resp = client.post(
            "/api/v1/support/tickets", headers=cheaders,
            json={"category": "NOT_A_CATEGORY", "subject": "x", "message": "x"},
        )
        assert resp.status_code == 422

    def test_vendor_and_rider_can_also_open_tickets(self, client, vendor, rider, login_as):
        vheaders = login_as(client, "vendor@example.com")
        rheaders = login_as(client, "rider@example.com")
        assert self.open_ticket(client, vheaders, category="VENDOR_ISSUE")["requester"]["role"] == "VENDOR"
        assert self.open_ticket(client, rheaders, category="RIDER_ISSUE")["requester"]["role"] == "RIDER"


class TestTicketOwnerView(_F):
    def test_customer_sees_own_tickets_only(self, client, customer, customer2, login_as):
        cheaders = login_as(client, "customer@example.com")
        c2headers = login_as(client, "customer2@example.com")
        self.open_ticket(client, cheaders, subject="Mine")
        self.open_ticket(client, c2headers, subject="Not mine")

        resp = client.get("/api/v1/support/tickets", headers=cheaders)
        tickets = resp.get_json()["data"]["tickets"]
        assert len(tickets) == 1
        assert tickets[0]["subject"] == "Mine"

    def test_customer_cannot_view_someone_elses_ticket(self, client, customer, customer2, login_as):
        cheaders = login_as(client, "customer@example.com")
        c2headers = login_as(client, "customer2@example.com")
        ticket = self.open_ticket(client, cheaders)

        resp = client.get(f"/api/v1/support/tickets/{ticket['id']}", headers=c2headers)
        assert resp.status_code == 404

    def test_customer_can_reply_to_own_ticket(self, client, customer, login_as):
        cheaders = login_as(client, "customer@example.com")
        ticket = self.open_ticket(client, cheaders)
        resp = client.post(f"/api/v1/support/tickets/{ticket['id']}/messages", headers=cheaders, json={"body": "Any update?"})
        assert resp.status_code == 201

        detail = client.get(f"/api/v1/support/tickets/{ticket['id']}", headers=cheaders).get_json()["data"]["ticket"]
        assert len(detail["messages"]) == 2

    def test_cannot_reply_to_closed_ticket(self, client, customer, support_agent, login_as):
        cheaders = login_as(client, "customer@example.com")
        aheaders = login_as(client, "agent@example.com")
        ticket = self.open_ticket(client, cheaders)
        client.patch(f"/api/v1/admin/support/tickets/{ticket['id']}/status", headers=aheaders, json={"status": "CLOSED"})

        resp = client.post(f"/api/v1/support/tickets/{ticket['id']}/messages", headers=cheaders, json={"body": "Hello?"})
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "TICKET_CLOSED"


class TestAgentWorkspace(_F):
    def test_agent_can_list_and_assign(self, client, customer, support_agent, login_as):
        cheaders = login_as(client, "customer@example.com")
        aheaders = login_as(client, "agent@example.com")
        ticket = self.open_ticket(client, cheaders)

        listing = client.get("/api/v1/admin/support/tickets", headers=aheaders)
        assert listing.status_code == 200
        assert listing.get_json()["data"]["pagination"]["total"] == 1

        assign = client.post(
            f"/api/v1/admin/support/tickets/{ticket['id']}/assign", headers=aheaders,
            json={"agent_id": client.get("/api/v1/auth/me", headers=aheaders).get_json()["data"]["user"]["id"]},
        )
        assert assign.status_code == 200
        assigned = assign.get_json()["data"]["ticket"]
        assert assigned["assigned_agent"]["id"] is not None
        assert assigned["status"] == "IN_PROGRESS"

    def test_moderator_cannot_access_support_queue(self, client, moderator, login_as):
        mheaders = login_as(client, "moderator@example.com")
        resp = client.get("/api/v1/admin/support/tickets", headers=mheaders)
        assert resp.status_code == 403

    def test_agent_public_reply_visible_to_customer_internal_note_is_not(self, client, customer, support_agent, login_as):
        cheaders = login_as(client, "customer@example.com")
        aheaders = login_as(client, "agent@example.com")
        ticket = self.open_ticket(client, cheaders)

        client.post(f"/api/v1/admin/support/tickets/{ticket['id']}/messages", headers=aheaders,
                    json={"body": "Looking into it", "visibility": "PUBLIC"})
        client.post(f"/api/v1/admin/support/tickets/{ticket['id']}/messages", headers=aheaders,
                    json={"body": "Customer seems confused, escalate", "visibility": "INTERNAL"})

        customer_view = client.get(f"/api/v1/support/tickets/{ticket['id']}", headers=cheaders).get_json()["data"]["ticket"]
        bodies = [m["body"] for m in customer_view["messages"]]
        assert "Looking into it" in bodies
        assert "Customer seems confused, escalate" not in bodies

        agent_view = client.get(f"/api/v1/admin/support/tickets/{ticket['id']}", headers=aheaders).get_json()["data"]["ticket"]
        assert len(agent_view["messages"]) == 3  # initial + public reply + internal note

    def test_agent_reply_transitions_open_to_in_progress(self, client, customer, support_agent, login_as):
        cheaders = login_as(client, "customer@example.com")
        aheaders = login_as(client, "agent@example.com")
        ticket = self.open_ticket(client, cheaders)
        assert ticket["status"] == "OPEN"

        client.post(f"/api/v1/admin/support/tickets/{ticket['id']}/messages", headers=aheaders, json={"body": "hi"})
        refreshed = client.get(f"/api/v1/admin/support/tickets/{ticket['id']}", headers=aheaders).get_json()["data"]["ticket"]
        assert refreshed["status"] == "IN_PROGRESS"

    def test_agent_can_resolve_ticket(self, client, customer, support_agent, login_as):
        cheaders = login_as(client, "customer@example.com")
        aheaders = login_as(client, "agent@example.com")
        ticket = self.open_ticket(client, cheaders)

        resp = client.patch(
            f"/api/v1/admin/support/tickets/{ticket['id']}/status", headers=aheaders,
            json={"status": "RESOLVED", "resolution_summary": "Password reset sent."},
        )
        assert resp.status_code == 200
        resolved = resp.get_json()["data"]["ticket"]
        assert resolved["status"] == "RESOLVED"
        assert resolved["resolved_at"] is not None
        assert resolved["resolution_summary"] == "Password reset sent."

    def test_attachment_add_and_visibility(self, client, customer, support_agent, login_as):
        cheaders = login_as(client, "customer@example.com")
        aheaders = login_as(client, "agent@example.com")
        ticket = self.open_ticket(client, cheaders)

        resp = client.post(
            f"/api/v1/support/tickets/{ticket['id']}/attachments", headers=cheaders,
            json={"filename": "screenshot.png", "reference": "s3://bucket/key.png", "content_type": "image/png"},
        )
        assert resp.status_code == 201

        agent_detail = client.get(f"/api/v1/admin/support/tickets/{ticket['id']}", headers=aheaders).get_json()["data"]["ticket"]
        assert len(agent_detail["attachments"]) == 1
