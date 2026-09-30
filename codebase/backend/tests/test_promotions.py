from decimal import Decimal

from tests.growth_fixtures import GrowthFixtures


class TestPromotionApplication(GrowthFixtures):
    def test_customer_can_apply_a_percentage_code_and_it_discounts_the_order(
        self, client, vendor, customer, admin, login_as
    ):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, _zone, product = self.setup_branch_with_zone(client, vheaders)
        promotion, resp = self.create_promotion(client, vheaders, code="SAVE10", value="10")
        assert resp.status_code == 201

        address = self.make_address(client, cheaders)
        client.post(
            "/api/v1/cart/items", headers=cheaders,
            json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 2},
        )
        apply_resp = client.post(
            f"/api/v1/cart/promotion?branch_id={branch['id']}", headers=cheaders, json={"code": "save10"}
        )
        assert apply_resp.status_code == 200

        summary = client.get(
            f"/api/v1/checkout/summary?branch_id={branch['id']}&address_id={address['id']}", headers=cheaders
        ).get_json()["data"]
        subtotal = Decimal(summary["subtotal"])
        expected_discount = (subtotal * Decimal("0.10")).quantize(Decimal("0.01"))
        assert Decimal(summary["discount_total"]) == expected_discount
        assert Decimal(summary["total"]) == subtotal - expected_discount + Decimal(summary["fees"])

        order = client.post(
            "/api/v1/orders", headers=cheaders, json={"branch_id": branch["id"], "address_id": address["id"]}
        ).get_json()["data"]["order"]
        assert Decimal(order["discount_total"]) == expected_discount
        assert order["applied_promotion"]["code"] == "SAVE10"
        assert Decimal(order["total"]) == subtotal - expected_discount + Decimal(order["fees"])

    def test_percentage_discount_is_capped_by_max_discount_amount(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, _zone, product = self.setup_branch_with_zone(client, vheaders)
        self.create_promotion(client, vheaders, code="BIG50", value="50", max_discount_amount="1.00")

        address = self.make_address(client, cheaders)
        client.post(
            "/api/v1/cart/items", headers=cheaders,
            json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 3},
        )
        client.post(f"/api/v1/cart/promotion?branch_id={branch['id']}", headers=cheaders, json={"code": "BIG50"})
        order = client.post(
            "/api/v1/orders", headers=cheaders, json={"branch_id": branch["id"], "address_id": address["id"]}
        ).get_json()["data"]["order"]
        assert Decimal(order["discount_total"]) == Decimal("1.00")

    def test_free_delivery_promotion_zeroes_out_the_delivery_fee(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, _zone, product = self.setup_branch_with_zone(client, vheaders)
        self.create_promotion(client, vheaders, code="FREEDEL", type="FREE_DELIVERY", value="0")

        address = self.make_address(client, cheaders)
        client.post(
            "/api/v1/cart/items", headers=cheaders,
            json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 1},
        )
        client.post(f"/api/v1/cart/promotion?branch_id={branch['id']}", headers=cheaders, json={"code": "FREEDEL"})
        order = client.post(
            "/api/v1/orders", headers=cheaders, json={"branch_id": branch["id"], "address_id": address["id"]}
        ).get_json()["data"]["order"]
        assert Decimal(order["discount_total"]) == Decimal(order["fees"])
        assert Decimal(order["total"]) == Decimal(order["subtotal"])

    def test_min_subtotal_not_met_is_rejected(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, _zone, product = self.setup_branch_with_zone(client, vheaders)
        self.create_promotion(client, vheaders, code="BIGORDER", value="10", min_subtotal="500.00")

        client.post(
            "/api/v1/cart/items", headers=cheaders,
            json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 1},
        )
        resp = client.post(f"/api/v1/cart/promotion?branch_id={branch['id']}", headers=cheaders, json={"code": "BIGORDER"})
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "PROMOTION_MIN_SUBTOTAL_NOT_MET"

    def test_code_scoped_to_one_vendor_does_not_apply_at_another_vendor(
        self, client, vendor, vendor2, customer, login_as
    ):
        vheaders = login_as(client, "vendor@example.com")
        vheaders2 = login_as(client, "vendor2@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, _zone, product = self.setup_branch_with_zone(client, vheaders)
        branch2, _zone2, product2 = self.setup_branch_with_zone(client, vheaders2, lat=41.0, lng=-73.0)
        self.create_promotion(client, vheaders, code="ONLYV1", value="10")

        client.post(
            "/api/v1/cart/items", headers=cheaders,
            json={"branch_id": branch2["id"], "product_id": product2["id"], "quantity": 1},
        )
        resp = client.post(f"/api/v1/cart/promotion?branch_id={branch2['id']}", headers=cheaders, json={"code": "ONLYV1"})
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "PROMOTION_NOT_APPLICABLE_TO_CART"

    def test_customer_cannot_use_a_code_more_than_its_per_customer_limit(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, _zone, product = self.setup_branch_with_zone(client, vheaders)
        self.create_promotion(client, vheaders, code="ONCE", value="10", usage_limit_per_customer=1)

        address = self.make_address(client, cheaders)

        def buy_and_apply():
            client.post(
                "/api/v1/cart/items", headers=cheaders,
                json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 1},
            )
            client.post(f"/api/v1/cart/promotion?branch_id={branch['id']}", headers=cheaders, json={"code": "ONCE"})
            return client.post(
                "/api/v1/orders", headers=cheaders, json={"branch_id": branch["id"], "address_id": address["id"]}
            )

        first = buy_and_apply()
        assert first.status_code == 201
        first_order = first.get_json()["data"]["order"]
        assert Decimal(first_order["discount_total"]) > 0

        second = buy_and_apply()
        assert second.status_code == 201
        second_order = second.get_json()["data"]["order"]
        # The code was auto-carried on the new cart (still attached) but is
        # no longer usable - reserve_usage re-validates it at order-creation
        # time and it silently prices at zero rather than blocking checkout.
        assert Decimal(second_order["discount_total"]) == Decimal("0")

    def test_cancelling_an_order_releases_the_promotion_slot_for_reuse(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, _zone, product = self.setup_branch_with_zone(client, vheaders)
        self.create_promotion(client, vheaders, code="REUSE", value="10", usage_limit_per_customer=1)
        address = self.make_address(client, cheaders)

        client.post(
            "/api/v1/cart/items", headers=cheaders,
            json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 1},
        )
        client.post(f"/api/v1/cart/promotion?branch_id={branch['id']}", headers=cheaders, json={"code": "REUSE"})
        order = client.post(
            "/api/v1/orders", headers=cheaders, json={"branch_id": branch["id"], "address_id": address["id"]}
        ).get_json()["data"]["order"]
        assert Decimal(order["discount_total"]) > 0

        client.post(f"/api/v1/orders/{order['id']}/cancel", headers=cheaders, json={})

        client.post(
            "/api/v1/cart/items", headers=cheaders,
            json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 1},
        )
        client.post(f"/api/v1/cart/promotion?branch_id={branch['id']}", headers=cheaders, json={"code": "REUSE"})
        second_order = client.post(
            "/api/v1/orders", headers=cheaders, json={"branch_id": branch["id"], "address_id": address["id"]}
        ).get_json()["data"]["order"]
        assert Decimal(second_order["discount_total"]) > 0

    def test_commission_is_calculated_on_the_post_discount_subtotal(
        self, client, vendor, customer, rider, admin, login_as
    ):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        self.create_promotion(client, vheaders, code="COMM10", value="10")

        self.onboard_available_rider(client, aheaders, rheaders, zone["id"])
        address = self.make_address(client, cheaders)
        client.post(
            "/api/v1/cart/items", headers=cheaders,
            json={"branch_id": branch["id"], "product_id": product["id"], "quantity": 2},
        )
        client.post(f"/api/v1/cart/promotion?branch_id={branch['id']}", headers=cheaders, json={"code": "COMM10"})
        order = client.post(
            "/api/v1/orders", headers=cheaders, json={"branch_id": branch["id"], "address_id": address["id"]}
        ).get_json()["data"]["order"]
        client.post("/api/v1/payments", headers=cheaders, json={"order_id": order["id"]})
        order = self.advance_to_ready(client, vheaders, order)

        offer = client.get("/api/v1/rider/delivery-offers", headers=rheaders).get_json()["data"]["offers"][0]
        delivery = client.post(
            f"/api/v1/rider/delivery-offers/{offer['id']}/accept", headers=rheaders
        ).get_json()["data"]["delivery"]
        client.post(f"/api/v1/deliveries/{delivery['id']}/pickup", headers=rheaders)
        client.post(f"/api/v1/deliveries/{delivery['id']}/start", headers=rheaders)
        client.post(f"/api/v1/deliveries/{delivery['id']}/complete", headers=rheaders)

        discounted_subtotal = Decimal(order["subtotal"]) - Decimal(order["discount_total"])
        expected_commission = (discounted_subtotal * Decimal("0.15")).quantize(Decimal("0.01"))
        expected_vendor_earnings = discounted_subtotal - expected_commission

        vendor_summary = client.get("/api/v1/vendor/financial-summary", headers=vheaders).get_json()["data"]
        assert Decimal(vendor_summary["account"]["payable_balance"]) == expected_vendor_earnings

        reconciliation = client.get("/api/v1/admin/reconciliation/summary", headers=aheaders).get_json()["data"]
        assert reconciliation["balanced"] is True


class TestPromotionManagement(GrowthFixtures):
    def test_vendor_cannot_scope_a_promotion_to_another_vendors_product(
        self, client, vendor, vendor2, login_as
    ):
        vheaders = login_as(client, "vendor@example.com")
        vheaders2 = login_as(client, "vendor2@example.com")
        _branch, _zone, product = self.setup_branch_with_zone(client, vheaders)

        resp = client.post(
            "/api/v1/vendor/promotions", headers=vheaders2,
            json={"name": "Sneaky", "type": "PERCENTAGE", "value": "10", "scope_type": "PRODUCT", "scope_target_ids": [product["id"]]},
        )
        assert resp.status_code == 403

    def test_admin_can_create_a_platform_wide_promotion(self, client, admin, login_as):
        aheaders = login_as(client, "admin@example.com")
        promotion, resp = self.create_admin_promotion(client, aheaders, code="PLATFORM5")
        assert resp.status_code == 201
        assert promotion["vendor_id"] is None

    def test_a_duplicate_code_is_rejected(self, client, vendor, login_as):
        vheaders = login_as(client, "vendor@example.com")
        self.create_promotion(client, vheaders, code="DUPE")
        _promotion, resp = self.create_promotion(client, vheaders, code="dupe")
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "PROMOTION_CODE_TAKEN"

    def test_vendor_cannot_see_another_vendors_promotion(self, client, vendor, vendor2, login_as):
        vheaders = login_as(client, "vendor@example.com")
        vheaders2 = login_as(client, "vendor2@example.com")
        promotion, _resp = self.create_promotion(client, vheaders, code="MINE")
        resp = client.get(f"/api/v1/vendor/promotions/{promotion['id']}", headers=vheaders2)
        assert resp.status_code == 404
