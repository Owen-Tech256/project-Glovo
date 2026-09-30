from tests.logistics_fixtures import LogisticsFixtures, BRANCH_LAT, BRANCH_LNG


class TestDeliveryCreation(LogisticsFixtures):
    def test_delivery_created_when_order_becomes_ready(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, _zone, product = self.setup_branch_with_zone(client, vheaders)
        self.place_order_to_ready(client, vheaders, cheaders, branch, product)

        order = client.get("/api/v1/orders", headers=cheaders).get_json()["data"]["orders"][0]
        resp = client.get(f"/api/v1/orders/{order['id']}/delivery", headers=cheaders)
        assert resp.status_code == 200
        delivery = resp.get_json()["data"]["delivery"]
        assert delivery["status"] == "SEARCHING"
        assert delivery["order_id"] == order["id"]

    def test_delivery_creation_is_idempotent(self, app, db, client, vendor, customer, login_as):
        from app.logistics.dispatch_service import create_delivery_and_dispatch
        from app.models.order import Order

        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, _zone, product = self.setup_branch_with_zone(client, vheaders)
        self.place_order_to_ready(client, vheaders, cheaders, branch, product)

        with app.app_context():
            order = Order.query.first()
            delivery1, created1 = create_delivery_and_dispatch(order)
            delivery2, created2 = create_delivery_and_dispatch(order)
            assert created1 is False  # already created by the READY transition hook
            assert delivery1.id == delivery2.id
            assert created2 is False

    def test_order_without_ready_has_no_delivery(self, client, vendor, customer, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        branch, _zone, product = self.setup_branch_with_zone(client, vheaders)
        order = self.place_order(client, vheaders, cheaders, branch, product)

        resp = client.get(f"/api/v1/orders/{order['id']}/delivery", headers=cheaders)
        assert resp.status_code == 404


class TestCandidateFiltering(LogisticsFixtures):
    def test_offer_goes_to_approved_online_zone_eligible_rider(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        self.onboard_available_rider(client, aheaders, rheaders, zone["id"])

        self.place_order_to_ready(client, vheaders, cheaders, branch, product)

        offers = client.get("/api/v1/rider/delivery-offers", headers=rheaders).get_json()["data"]["offers"]
        assert len(offers) == 1
        assert offers[0]["status"] == "OFFERED"

    def test_unapproved_rider_receives_no_offer(self, client, vendor, customer, rider, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        # Joins the zone and reports location but is never approved, so
        # going AVAILABLE itself is blocked - simulating "not dispatch
        # eligible" by leaving them OFFLINE/PENDING.
        client.post("/api/v1/rider/zones", headers=rheaders, json={"zone_id": zone["id"]})
        client.post("/api/v1/rider/location", headers=rheaders, json={"latitude": BRANCH_LAT, "longitude": BRANCH_LNG})

        self.place_order_to_ready(client, vheaders, cheaders, branch, product)

        offers = client.get("/api/v1/rider/delivery-offers", headers=rheaders).get_json()["data"]["offers"]
        assert offers == []

    def test_rider_outside_zone_receives_no_offer(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders, radius_meters=1000)
        self.approve_rider(client, aheaders, rheaders)
        # Far away - well outside the 1km zone radius.
        self.make_available(client, rheaders, zone_id=None, lat=41.9, lng=-87.6)
        # Never joins the branch's zone at all.

        self.place_order_to_ready(client, vheaders, cheaders, branch, product)

        offers = client.get("/api/v1/rider/delivery-offers", headers=rheaders).get_json()["data"]["offers"]
        assert offers == []

    def test_rider_with_stale_location_receives_no_offer(self, client, db, vendor, customer, rider, admin, login_as):
        from datetime import timedelta
        from app.models.rider import Rider
        from app.models.base import _utcnow

        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        self.onboard_available_rider(client, aheaders, rheaders, zone["id"])

        db_rider = Rider.query.filter_by(user_id=rider.id).first()
        db_rider.location_updated_at = _utcnow() - timedelta(seconds=1000)
        db.session.commit()

        self.place_order_to_ready(client, vheaders, cheaders, branch, product)

        offers = client.get("/api/v1/rider/delivery-offers", headers=rheaders).get_json()["data"]["offers"]
        assert offers == []

    def test_offline_rider_receives_no_offer(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        self.approve_rider(client, aheaders, rheaders)
        client.post("/api/v1/rider/zones", headers=rheaders, json={"zone_id": zone["id"]})
        client.post("/api/v1/rider/location", headers=rheaders, json={"latitude": BRANCH_LAT, "longitude": BRANCH_LNG})
        # Never goes AVAILABLE - stays OFFLINE.

        self.place_order_to_ready(client, vheaders, cheaders, branch, product)

        offers = client.get("/api/v1/rider/delivery-offers", headers=rheaders).get_json()["data"]["offers"]
        assert offers == []


class TestRankingAndOfferLifecycle(LogisticsFixtures):
    def test_nearest_rider_is_offered_first_when_batch_size_is_one(self, app, client, vendor, customer, rider, rider2, admin, login_as):
        app.config["DISPATCH_OFFER_BATCH_SIZE"] = 1
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        r1headers = login_as(client, "rider@example.com")
        r2headers = login_as(client, "rider2@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders, radius_meters=20000)

        self.approve_rider(client, aheaders, r1headers)
        self.approve_rider(client, aheaders, r2headers)
        # rider is far (but still in-zone); rider2 is essentially at the branch.
        self.make_available(client, r1headers, zone_id=zone["id"], lat=BRANCH_LAT + 0.05, lng=BRANCH_LNG + 0.05)
        self.make_available(client, r2headers, zone_id=zone["id"], lat=BRANCH_LAT, lng=BRANCH_LNG)

        self.place_order_to_ready(client, vheaders, cheaders, branch, product)

        offers1 = client.get("/api/v1/rider/delivery-offers", headers=r1headers).get_json()["data"]["offers"]
        offers2 = client.get("/api/v1/rider/delivery-offers", headers=r2headers).get_json()["data"]["offers"]
        assert offers1 == []
        assert len(offers2) == 1

    def test_accepting_offer_assigns_delivery_and_updates_order(self, client, vendor, customer, rider, admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        self.onboard_available_rider(client, aheaders, rheaders, zone["id"])
        self.place_order_to_ready(client, vheaders, cheaders, branch, product)

        offer = client.get("/api/v1/rider/delivery-offers", headers=rheaders).get_json()["data"]["offers"][0]
        resp = client.post(f"/api/v1/rider/delivery-offers/{offer['id']}/accept", headers=rheaders)
        assert resp.status_code == 200
        delivery = resp.get_json()["data"]["delivery"]
        assert delivery["status"] == "ASSIGNED"

        me = client.get("/api/v1/rider/me", headers=rheaders).get_json()["data"]["rider"]
        assert me["operational_status"] == "BUSY"

        order = client.get("/api/v1/orders", headers=cheaders).get_json()["data"]["orders"][0]
        assert order["status"] == "RIDER_ASSIGNED"

    def test_second_rider_cannot_claim_already_accepted_delivery(self, app, client, vendor, customer, rider, rider2, admin, login_as):
        app.config["DISPATCH_OFFER_BATCH_SIZE"] = 2
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        r1headers = login_as(client, "rider@example.com")
        r2headers = login_as(client, "rider2@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        self.onboard_available_rider(client, aheaders, r1headers, zone["id"])
        self.onboard_available_rider(client, aheaders, r2headers, zone["id"])

        self.place_order_to_ready(client, vheaders, cheaders, branch, product)

        offer1 = client.get("/api/v1/rider/delivery-offers", headers=r1headers).get_json()["data"]["offers"][0]
        offer2 = client.get("/api/v1/rider/delivery-offers", headers=r2headers).get_json()["data"]["offers"][0]

        accept1 = client.post(f"/api/v1/rider/delivery-offers/{offer1['id']}/accept", headers=r1headers)
        assert accept1.status_code == 200

        accept2 = client.post(f"/api/v1/rider/delivery-offers/{offer2['id']}/accept", headers=r2headers)
        assert accept2.status_code == 409
        # rider1's acceptance immediately cancels every other pending offer
        # for the same delivery (see dispatch_service.accept_offer), so
        # rider2's own assignment row is already CANCELLED by the time they
        # try - OFFER_UNAVAILABLE. If the two accepts had instead raced at
        # the exact same instant, the delivery-level lock would produce
        # DELIVERY_ALREADY_CLAIMED instead; either way, exactly one rider
        # wins and the loser is rejected with a 409.
        assert accept2.get_json()["error"]["code"] in ("OFFER_UNAVAILABLE", "DELIVERY_ALREADY_CLAIMED")

        me2 = client.get("/api/v1/rider/me", headers=r2headers).get_json()["data"]["rider"]
        assert me2["operational_status"] == "AVAILABLE"

    def test_reject_offer_returns_delivery_to_searching_with_no_other_candidates(
        self, client, vendor, customer, rider, admin, login_as
    ):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        self.onboard_available_rider(client, aheaders, rheaders, zone["id"])
        self.place_order_to_ready(client, vheaders, cheaders, branch, product)

        offer = client.get("/api/v1/rider/delivery-offers", headers=rheaders).get_json()["data"]["offers"][0]
        resp = client.post(
            f"/api/v1/rider/delivery-offers/{offer['id']}/reject", headers=rheaders, json={"reason": "Too far"}
        )
        assert resp.status_code == 200

        order = client.get("/api/v1/orders", headers=cheaders).get_json()["data"]["orders"][0]
        delivery = client.get(f"/api/v1/orders/{order['id']}/delivery", headers=cheaders).get_json()["data"]["delivery"]
        assert delivery["status"] == "SEARCHING"
        assert delivery["rider_id"] is None

        # The rider who rejected is never re-offered the same delivery.
        offers_after = client.get("/api/v1/rider/delivery-offers", headers=rheaders).get_json()["data"]["offers"]
        assert offers_after == []

    def test_accepting_expired_offer_is_rejected(self, app, db, client, vendor, customer, rider, admin, login_as):
        from app.models.delivery_assignment import DeliveryAssignment
        from app.models.base import _utcnow
        from datetime import timedelta

        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        self.onboard_available_rider(client, aheaders, rheaders, zone["id"])
        self.place_order_to_ready(client, vheaders, cheaders, branch, product)

        offer = client.get("/api/v1/rider/delivery-offers", headers=rheaders).get_json()["data"]["offers"][0]
        with app.app_context():
            assignment = DeliveryAssignment.query.filter_by(public_id=offer["id"]).first()
            assignment.expires_at = _utcnow() - timedelta(seconds=5)
            db.session.commit()

        resp = client.post(f"/api/v1/rider/delivery-offers/{offer['id']}/accept", headers=rheaders)
        assert resp.status_code in (409, 404)

    def test_expired_offer_redispatches_to_next_candidate(
        self, app, db, client, vendor, customer, rider, rider2, admin, login_as
    ):
        from app.models.delivery_assignment import DeliveryAssignment
        from app.models.base import _utcnow
        from datetime import timedelta

        app.config["DISPATCH_OFFER_BATCH_SIZE"] = 1
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        r1headers = login_as(client, "rider@example.com")
        r2headers = login_as(client, "rider2@example.com")
        aheaders = login_as(client, "admin@example.com")
        branch, zone, product = self.setup_branch_with_zone(client, vheaders, radius_meters=20000)
        # rider is nearer, so is offered first (batch size 1).
        self.approve_rider(client, aheaders, r1headers)
        self.approve_rider(client, aheaders, r2headers)
        self.make_available(client, r1headers, zone_id=zone["id"], lat=BRANCH_LAT, lng=BRANCH_LNG)
        self.make_available(client, r2headers, zone_id=zone["id"], lat=BRANCH_LAT + 0.05, lng=BRANCH_LNG + 0.05)

        self.place_order_to_ready(client, vheaders, cheaders, branch, product)
        offer1 = client.get("/api/v1/rider/delivery-offers", headers=r1headers).get_json()["data"]["offers"]
        assert len(offer1) == 1

        with app.app_context():
            assignment = DeliveryAssignment.query.filter_by(public_id=offer1[0]["id"]).first()
            assignment.expires_at = _utcnow() - timedelta(seconds=5)
            db.session.commit()

        # rider2 checking their offers triggers the lazy expiry sweep and
        # redispatch to the next candidate.
        offers2 = client.get("/api/v1/rider/delivery-offers", headers=r2headers).get_json()["data"]["offers"]
        assert len(offers2) == 1

        offers1_after = client.get("/api/v1/rider/delivery-offers", headers=r1headers).get_json()["data"]["offers"]
        assert offers1_after == []
