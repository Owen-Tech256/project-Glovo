from decimal import Decimal

from tests.growth_fixtures import GrowthFixtures


class TestReviewEligibility(GrowthFixtures):
    def test_order_is_not_reviewable_until_delivered(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, _zone, product = self.setup_branch_with_zone(client, vheaders)
        order = self.place_order(client, vheaders, cheaders, branch, product)

        resp = client.get(f"/api/v1/orders/{order['id']}/reviews", headers=cheaders)
        assert resp.get_json()["data"]["reviewable"] == []

    def test_delivered_order_makes_vendor_and_rider_reviewable(
        self, client, vendor, customer, rider, admin, login_as
    ):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        order, _delivery = self.deliver_full_order(client, vheaders, cheaders, rheaders, aheaders, branch, zone, product)

        reviewable = client.get(f"/api/v1/orders/{order['id']}/reviews", headers=cheaders).get_json()["data"]["reviewable"]
        target_types = {item["target_type"] for item in reviewable}
        assert "VENDOR" in target_types
        assert "RIDER" in target_types
        assert "PRODUCT" in target_types
        assert all(item["existing_review"] is None for item in reviewable)

    def test_customer_can_submit_and_the_target_rating_aggregate_updates(
        self, client, vendor, customer, rider, admin, login_as
    ):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        order, _delivery = self.deliver_full_order(client, vheaders, cheaders, rheaders, aheaders, branch, zone, product)
        reviewable = client.get(f"/api/v1/orders/{order['id']}/reviews", headers=cheaders).get_json()["data"]["reviewable"]
        vendor_target = next(t for t in reviewable if t["target_type"] == "VENDOR")

        resp = client.post(
            f"/api/v1/orders/{order['id']}/reviews", headers=cheaders,
            json={"target_type": "VENDOR", "target_id": vendor_target["target_id"], "rating": 5, "body": "Great!"},
        )
        assert resp.status_code == 201

        vendor_reviews = client.get(f"/api/v1/vendors/{vendor_target['target_id']}/reviews").get_json()["data"]["reviews"]
        assert len(vendor_reviews) == 1
        assert vendor_reviews[0]["rating"] == 5

    def test_customer_cannot_review_the_same_target_twice_on_one_order(
        self, client, vendor, customer, rider, admin, login_as
    ):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        order, _delivery = self.deliver_full_order(client, vheaders, cheaders, rheaders, aheaders, branch, zone, product)
        reviewable = client.get(f"/api/v1/orders/{order['id']}/reviews", headers=cheaders).get_json()["data"]["reviewable"]
        vendor_target = next(t for t in reviewable if t["target_type"] == "VENDOR")

        client.post(
            f"/api/v1/orders/{order['id']}/reviews", headers=cheaders,
            json={"target_type": "VENDOR", "target_id": vendor_target["target_id"], "rating": 4},
        )
        second = client.post(
            f"/api/v1/orders/{order['id']}/reviews", headers=cheaders,
            json={"target_type": "VENDOR", "target_id": vendor_target["target_id"], "rating": 2},
        )
        assert second.status_code == 422
        assert second.get_json()["error"]["code"] == "REVIEW_ALREADY_EXISTS"

    def test_vendor_can_respond_to_a_review_of_themselves(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        order, _delivery = self.deliver_full_order(client, vheaders, cheaders, rheaders, aheaders, branch, zone, product)
        reviewable = client.get(f"/api/v1/orders/{order['id']}/reviews", headers=cheaders).get_json()["data"]["reviewable"]
        vendor_target = next(t for t in reviewable if t["target_type"] == "VENDOR")

        review = client.post(
            f"/api/v1/orders/{order['id']}/reviews", headers=cheaders,
            json={"target_type": "VENDOR", "target_id": vendor_target["target_id"], "rating": 3, "body": "It was okay."},
        ).get_json()["data"]["review"]

        resp = client.post(
            f"/api/v1/reviews/{review['id']}/response", headers=vheaders, json={"body": "Thanks for the feedback!"}
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["review"]["response"]["body"] == "Thanks for the feedback!"

        vendor_reviews = client.get("/api/v1/vendor/reviews", headers=vheaders).get_json()["data"]["reviews"]
        assert len(vendor_reviews) == 1

    def test_rider_cannot_respond_to_a_review_of_the_vendor(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        order, _delivery = self.deliver_full_order(client, vheaders, cheaders, rheaders, aheaders, branch, zone, product)
        reviewable = client.get(f"/api/v1/orders/{order['id']}/reviews", headers=cheaders).get_json()["data"]["reviewable"]
        vendor_target = next(t for t in reviewable if t["target_type"] == "VENDOR")

        review = client.post(
            f"/api/v1/orders/{order['id']}/reviews", headers=cheaders,
            json={"target_type": "VENDOR", "target_id": vendor_target["target_id"], "rating": 3},
        ).get_json()["data"]["review"]

        resp = client.post(f"/api/v1/reviews/{review['id']}/response", headers=rheaders, json={"body": "Not mine!"})
        assert resp.status_code == 403

    def test_reporting_a_review_hides_it_from_public_view_pending_moderation(
        self, client, vendor, customer, rider, admin, login_as
    ):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        order, _delivery = self.deliver_full_order(client, vheaders, cheaders, rheaders, aheaders, branch, zone, product)
        reviewable = client.get(f"/api/v1/orders/{order['id']}/reviews", headers=cheaders).get_json()["data"]["reviewable"]
        vendor_target = next(t for t in reviewable if t["target_type"] == "VENDOR")

        review = client.post(
            f"/api/v1/orders/{order['id']}/reviews", headers=cheaders,
            json={"target_type": "VENDOR", "target_id": vendor_target["target_id"], "rating": 1, "body": "unfair"},
        ).get_json()["data"]["review"]

        client.post(f"/api/v1/reviews/{review['id']}/report", headers=vheaders, json={"reason": "Abusive"})
        public_reviews = client.get(f"/api/v1/vendors/{vendor_target['target_id']}/reviews").get_json()["data"]["reviews"]
        assert public_reviews == []

        reports = client.get("/api/v1/admin/review-reports", headers=aheaders).get_json()["data"]["reports"]
        assert len(reports) == 1
        report_id = reports[0]["id"]

        resolve = client.patch(
            f"/api/v1/admin/review-reports/{report_id}", headers=aheaders, json={"status": "DISMISSED"}
        )
        assert resolve.status_code == 200

    def test_admin_can_hide_a_review_directly(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        order, _delivery = self.deliver_full_order(client, vheaders, cheaders, rheaders, aheaders, branch, zone, product)
        reviewable = client.get(f"/api/v1/orders/{order['id']}/reviews", headers=cheaders).get_json()["data"]["reviewable"]
        vendor_target = next(t for t in reviewable if t["target_type"] == "VENDOR")
        review = client.post(
            f"/api/v1/orders/{order['id']}/reviews", headers=cheaders,
            json={"target_type": "VENDOR", "target_id": vendor_target["target_id"], "rating": 5},
        ).get_json()["data"]["review"]

        resp = client.patch(f"/api/v1/admin/reviews/{review['id']}/moderate", headers=aheaders, json={"status": "HIDDEN"})
        assert resp.status_code == 200
        public_reviews = client.get(f"/api/v1/vendors/{vendor_target['target_id']}/reviews").get_json()["data"]["reviews"]
        assert public_reviews == []

    def test_customer_can_withdraw_their_own_review(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        order, _delivery = self.deliver_full_order(client, vheaders, cheaders, rheaders, aheaders, branch, zone, product)
        reviewable = client.get(f"/api/v1/orders/{order['id']}/reviews", headers=cheaders).get_json()["data"]["reviewable"]
        vendor_target = next(t for t in reviewable if t["target_type"] == "VENDOR")
        review = client.post(
            f"/api/v1/orders/{order['id']}/reviews", headers=cheaders,
            json={"target_type": "VENDOR", "target_id": vendor_target["target_id"], "rating": 2},
        ).get_json()["data"]["review"]

        resp = client.delete(f"/api/v1/reviews/{review['id']}", headers=cheaders)
        assert resp.status_code == 200
        public_reviews = client.get(f"/api/v1/vendors/{vendor_target['target_id']}/reviews").get_json()["data"]["reviews"]
        assert public_reviews == []
