"""
Shared setup helpers for the Phase 4 logistics test suite - not collected
by pytest itself (pytest.ini's python_files = test_*.py), mirroring how
tests/test_vendor_orders.py's _VendorOrderFixtures mixin works within a
single file, just promoted to a shared module since several new test files
all need "a READY order" and "an online, zone-eligible rider" as a starting
point.
"""

BRANCH_LAT = 40.7128
BRANCH_LNG = -74.0060


class LogisticsFixtures:
    def setup_branch_with_zone(self, client, vheaders, radius_meters=5000, lat=BRANCH_LAT, lng=BRANCH_LNG):
        branch = client.post(
            "/api/v1/vendors/me/branches", headers=vheaders,
            json={"name": "Branch", "address": "1 Main St", "latitude": lat, "longitude": lng},
        ).get_json()["data"]["branch"]
        zone = client.post(
            f"/api/v1/vendors/me/branches/{branch['id']}/zones", headers=vheaders,
            json={"name": "zone", "center_latitude": lat, "center_longitude": lng, "radius_meters": radius_meters},
        ).get_json()["data"]["delivery_zone"]
        category = client.post(
            "/api/v1/vendors/me/categories", headers=vheaders, json={"name": "Pizzas"}
        ).get_json()["data"]["category"]
        product = client.post(
            "/api/v1/vendors/me/products", headers=vheaders,
            json={"category_id": category["id"], "name": "Margherita", "price": "9.99"},
        ).get_json()["data"]["product"]
        client.put(
            f"/api/v1/vendors/me/branches/{branch['id']}/products/{product['id']}", headers=vheaders,
            json={"availability_status": "AVAILABLE"},
        )
        return branch, zone, product

    def make_address(self, client, cheaders, lat=BRANCH_LAT, lng=BRANCH_LNG):
        payload = {
            "label": "Home", "recipient_name": "Cara Customer", "phone": "+12025550123",
            "address_line1": "123 Main St", "city": "New York", "country": "USA",
            "latitude": lat, "longitude": lng,
        }
        return client.post("/api/v1/addresses", headers=cheaders, json=payload).get_json()["data"]["address"]

    def place_order(self, client, vheaders, cheaders, branch, product):
        address = self.make_address(client, cheaders)
        client.post(
            "/api/v1/cart/items", headers=cheaders,
            json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 1},
        )
        order = client.post(
            "/api/v1/orders", headers=cheaders, json={"branch_id": branch["id"], "address_id": address["id"]}
        ).get_json()["data"]["order"]
        # Phase 5: an order no longer auto-confirms payment on creation -
        # pay it here so every existing logistics test (which assumes an
        # order is already PAYMENT_CONFIRMED and ready for the vendor to
        # act on) keeps working unchanged.
        client.post("/api/v1/payments", headers=cheaders, json={"order_id": order["id"]})
        return order

    def advance_to_ready(self, client, vheaders, order):
        url = f"/api/v1/vendor/orders/{order['id']}/transition"
        client.post(url, headers=vheaders, json={"to_status": "VENDOR_ACCEPTED"})
        client.post(url, headers=vheaders, json={"to_status": "PREPARING"})
        return client.post(url, headers=vheaders, json={"to_status": "READY"}).get_json()["data"]["order"]

    def place_order_to_ready(self, client, vheaders, cheaders, branch, product):
        order = self.place_order(client, vheaders, cheaders, branch, product)
        return self.advance_to_ready(client, vheaders, order)

    def get_rider_id(self, client, rider_headers):
        return client.get("/api/v1/rider/me", headers=rider_headers).get_json()["data"]["rider"]["id"]

    def approve_rider(self, client, admin_headers, rider_headers):
        rider_id = self.get_rider_id(client, rider_headers)
        client.patch(f"/api/v1/admin/riders/{rider_id}/status", headers=admin_headers, json={"status": "UNDER_REVIEW"})
        client.patch(f"/api/v1/admin/riders/{rider_id}/status", headers=admin_headers, json={"status": "APPROVED"})
        return rider_id

    def make_available(self, client, rider_headers, zone_id=None, lat=BRANCH_LAT, lng=BRANCH_LNG):
        if zone_id:
            client.post("/api/v1/rider/zones", headers=rider_headers, json={"zone_id": zone_id})
        client.post("/api/v1/rider/location", headers=rider_headers, json={"latitude": lat, "longitude": lng})
        return client.patch("/api/v1/rider/availability", headers=rider_headers, json={"status": "AVAILABLE"})

    def onboard_available_rider(self, client, admin_headers, rider_headers, zone_id, lat=BRANCH_LAT, lng=BRANCH_LNG):
        """The common case: approve + join zone + report location + go
        AVAILABLE, in one call."""
        self.approve_rider(client, admin_headers, rider_headers)
        self.make_available(client, rider_headers, zone_id=zone_id, lat=lat, lng=lng)
