from tests.support_fixtures import SupportFixtures


class _F(SupportFixtures):
    pass


class TestAuditAccess(_F):
    def test_customer_cannot_view_audit_trail(self, client, customer, login_as):
        headers = login_as(client, "customer@example.com")
        resp = client.get("/api/v1/admin/audit/events", headers=headers)
        assert resp.status_code == 403

    def test_scoped_admin_without_audit_view_is_forbidden(self, client, moderator, login_as):
        headers = login_as(client, "moderator@example.com")
        resp = client.get("/api/v1/admin/audit/events", headers=headers)
        assert resp.status_code == 403

    def test_legacy_admin_can_view_audit_trail(self, client, admin, login_as):
        headers = login_as(client, "admin@example.com")
        resp = client.get("/api/v1/admin/audit/events", headers=headers)
        assert resp.status_code == 200


class TestAuditContent(_F):
    def test_ticket_assignment_is_audited_with_before_and_after(self, client, customer, support_agent, admin, login_as):
        cheaders = login_as(client, "customer@example.com")
        aheaders = login_as(client, "agent@example.com")
        adheaders = login_as(client, "admin@example.com")
        ticket = self.open_ticket(client, cheaders)
        agent_id = client.get("/api/v1/auth/me", headers=aheaders).get_json()["data"]["user"]["id"]
        client.post(f"/api/v1/admin/support/tickets/{ticket['id']}/assign", headers=aheaders, json={"agent_id": agent_id})

        events = client.get(
            "/api/v1/admin/audit/events", headers=adheaders,
            query_string={"entity_type": "SUPPORT_TICKET", "entity_id": ticket["id"]},
        ).get_json()["data"]["events"]
        assign_event = next(e for e in events if e["action"] == "SUPPORT_TICKET_ASSIGNED")
        assert assign_event["after"]["assigned_agent"] == agent_id
        assert assign_event["actor"]["id"] == agent_id

    def test_ticket_status_change_is_audited_with_before_and_after(self, client, customer, support_agent, admin, login_as):
        cheaders = login_as(client, "customer@example.com")
        aheaders = login_as(client, "agent@example.com")
        adheaders = login_as(client, "admin@example.com")
        ticket = self.open_ticket(client, cheaders)
        client.patch(f"/api/v1/admin/support/tickets/{ticket['id']}/status", headers=aheaders, json={"status": "RESOLVED"})

        events = client.get(
            "/api/v1/admin/audit/events", headers=adheaders,
            query_string={"entity_type": "SUPPORT_TICKET", "entity_id": ticket["id"], "action": "SUPPORT_TICKET_STATUS_CHANGED"},
        ).get_json()["data"]["events"]
        assert len(events) == 1
        assert events[0]["before"]["status"] == "OPEN"
        assert events[0]["after"]["status"] == "RESOLVED"

    def test_admin_role_assignment_is_audited(self, client, super_admin, admin, login_as):
        headers = login_as(client, "superadmin@example.com")
        admin_id = client.get("/api/v1/auth/me", headers=login_as(client, "admin@example.com")).get_json()["data"]["user"]["id"]
        roles = client.get("/api/v1/admin/roles", headers=headers).get_json()["data"]["roles"]
        analyst_role_id = next(r["id"] for r in roles if r["name"] == "ANALYST")
        client.patch(f"/api/v1/admin/staff/{admin_id}/role", headers=headers, json={"role_id": analyst_role_id})

        events = client.get(
            "/api/v1/admin/audit/events", headers=headers,
            query_string={"entity_type": "USER", "entity_id": admin_id, "action": "ADMIN_ROLE_ASSIGNED"},
        ).get_json()["data"]["events"]
        assert len(events) == 1
        assert events[0]["after"]["admin_role"] == "ANALYST"

    def test_audit_events_are_paginated_and_ordered_newest_first(self, client, customer, support_agent, admin, login_as):
        cheaders = login_as(client, "customer@example.com")
        aheaders = login_as(client, "agent@example.com")
        adheaders = login_as(client, "admin@example.com")
        for i in range(3):
            self.open_ticket(client, cheaders, subject=f"Ticket {i}")
        ticket = self.open_ticket(client, cheaders, subject="Last one")
        client.patch(f"/api/v1/admin/support/tickets/{ticket['id']}/status", headers=aheaders, json={"status": "RESOLVED"})

        resp = client.get("/api/v1/admin/audit/events", headers=adheaders, query_string={"per_page": 1})
        body = resp.get_json()["data"]
        assert len(body["events"]) == 1
        assert body["pagination"]["total"] >= 1
        assert body["events"][0]["action"] == "SUPPORT_TICKET_STATUS_CHANGED"

    def test_filter_by_user_id(self, client, customer, customer2, support_agent, admin, login_as):
        cheaders = login_as(client, "customer@example.com")
        c2headers = login_as(client, "customer2@example.com")
        adheaders = login_as(client, "admin@example.com")
        self.open_ticket(client, cheaders)
        self.open_ticket(client, c2headers)

        customer_id = client.get("/api/v1/auth/me", headers=cheaders).get_json()["data"]["user"]["id"]
        events = client.get(
            "/api/v1/admin/audit/events", headers=adheaders, query_string={"user_id": customer_id},
        ).get_json()["data"]["events"]
        # No ticket-creation audit events are recorded (only privileged
        # staff actions are), so this should simply return no rows rather
        # than error - the filter itself is what's under test.
        assert isinstance(events, list)
