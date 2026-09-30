"""
Shared setup helpers for the Phase 5 money test suite, building on top of
LogisticsFixtures (Phase 4) the same way test_delivery_workflow.py etc. do.
"""
from tests.logistics_fixtures import LogisticsFixtures


class PaymentsFixtures(LogisticsFixtures):
    def place_unpaid_order(self, client, vheaders, cheaders, branch, product):
        """Unlike LogisticsFixtures.place_order (which now also pays, so
        every Phase 4 test keeps working unchanged), this leaves the order
        at PENDING_PAYMENT - what the payment tests themselves need to
        exercise the payment flow from a clean starting point."""
        address = self.make_address(client, cheaders)
        client.post(
            "/api/v1/cart/items", headers=cheaders,
            json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 1},
        )
        return client.post(
            "/api/v1/orders", headers=cheaders, json={"branch_id": branch["id"], "address_id": address["id"]}
        ).get_json()["data"]["order"]

    def deliver_full_order(self, client, vheaders, cheaders, rheaders, aheaders, branch, zone, product):
        """Takes an order all the way from cart to DELIVERED - the full
        journey settlement needs to have happened (settle_order only runs
        once a Delivery reaches DELIVERED)."""
        self.onboard_available_rider(client, aheaders, rheaders, zone["id"])
        order = self.place_order(client, vheaders, cheaders, branch, product)
        order = self.advance_to_ready(client, vheaders, order)

        offer = client.get("/api/v1/rider/delivery-offers", headers=rheaders).get_json()["data"]["offers"][0]
        delivery = client.post(
            f"/api/v1/rider/delivery-offers/{offer['id']}/accept", headers=rheaders
        ).get_json()["data"]["delivery"]

        client.post(f"/api/v1/deliveries/{delivery['id']}/pickup", headers=rheaders)
        client.post(f"/api/v1/deliveries/{delivery['id']}/start", headers=rheaders)
        client.post(f"/api/v1/deliveries/{delivery['id']}/complete", headers=rheaders)

        delivered_order = client.get(f"/api/v1/orders/{order['id']}", headers=cheaders).get_json()["data"]["order"]
        return delivered_order, delivery
