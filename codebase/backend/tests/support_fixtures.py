"""Shared setup helpers for the Phase 7 test suite, building on
PaymentsFixtures (Phase 5) the same way growth_fixtures.py does."""
from tests.payments_fixtures import PaymentsFixtures


class SupportFixtures(PaymentsFixtures):
    def open_ticket(self, client, headers, category="GENERAL", subject="Help", message="I need help.",
                     related_entity_type=None, related_entity_id=None):
        payload = {"category": category, "subject": subject, "message": message}
        if related_entity_type:
            payload["related_entity_type"] = related_entity_type
            payload["related_entity_id"] = related_entity_id
        return client.post("/api/v1/support/tickets", headers=headers, json=payload).get_json()["data"]["ticket"]

    def open_dispute(self, client, headers, order_id, category="MISSING_ITEM", description="Item missing."):
        return client.post(
            "/api/v1/disputes", headers=headers, json={"order_id": order_id, "category": category, "description": description}
        ).get_json()["data"]["dispute"]
