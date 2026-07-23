"""The offer/accept/decline/expire cycle — how an order actually reaches a rider."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from food.models import DeliveryOffer, FoodOrder, Restaurant, Rider
from food.services_dispatch import (accept_offer, decline_offer, assign_rider, offer_order,
                                    sweep_offers, OFFER_TTL_SECONDS)

User = get_user_model()
HERE = (Decimal("23.7104"), Decimal("90.9280"))


def make_rider(name, *, km_away=0, available=True, seen_minutes_ago=1):
    user = User.objects.create(username=f"u_{name}", email=f"{name}@x.com", role="Rider")
    return Rider.objects.create(
        user=user, name=name, is_available=available,
        current_lat=HERE[0] + Decimal(str(round(km_away / 111.0, 6))), current_lng=HERE[1],
        last_seen_at=timezone.now() - timedelta(minutes=seen_minutes_ago))


class OfferCycleTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(
            name="R", slug="r", status=Restaurant.Status.ACTIVE,
            pickup_lat=HERE[0], pickup_lng=HERE[1])

    def _order(self, **kw):
        defaults = dict(guest_name="G", guest_phone="017", delivery_address="A",
                        restaurant=self.restaurant, subtotal=Decimal("100"),
                        total=Decimal("100"), status=FoodOrder.Status.CONFIRMED,
                        rider_base_pay=Decimal("35.00"))
        defaults.update(kw)
        return FoodOrder.objects.create(**defaults)

    def test_the_nearest_rider_is_offered_first(self):
        near = make_rider("near", km_away=0.5)
        make_rider("far", km_away=5)
        offer = offer_order(self._order())
        self.assertEqual(offer.rider, near)

    def test_accepting_assigns_the_order_and_closes_the_offer(self):
        rider = make_rider("r1")
        order = self._order()
        offer = offer_order(order)
        got, ok = accept_offer(offer)
        self.assertTrue(ok)
        self.assertEqual(got.rider, rider)
        offer.refresh_from_db()
        self.assertEqual(offer.state, DeliveryOffer.State.ACCEPTED)

    def test_declining_cascades_to_the_next_rider(self):
        first = make_rider("first", km_away=0.5)
        second = make_rider("second", km_away=3)
        order = self._order()
        offer = offer_order(order)
        self.assertEqual(offer.rider, first)

        next_offer = decline_offer(offer)
        self.assertEqual(next_offer.rider, second)
        offer.refresh_from_db()
        self.assertEqual(offer.state, DeliveryOffer.State.REJECTED)

    def test_a_rider_who_declined_is_not_offered_the_same_order_again(self):
        only = make_rider("only")
        order = self._order()
        decline_offer(offer_order(order))
        # No one else to try, so the order is left for the admin queue rather
        # than pestering the rider who just said no.
        self.assertIsNone(offer_order(order))
        self.assertEqual(only.delivery_offers.filter(order=order).count(), 1)

    def test_an_expired_offer_cascades_on_the_next_sweep(self):
        first = make_rider("first", km_away=0.5)
        second = make_rider("second", km_away=3)
        order = self._order()
        offer = offer_order(order)
        # Force the deadline into the past.
        DeliveryOffer.objects.filter(pk=offer.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1))

        expired, re_offered = sweep_offers()
        self.assertEqual(expired, 1)
        self.assertEqual(re_offered, 1)
        offer.refresh_from_db()
        self.assertEqual(offer.state, DeliveryOffer.State.EXPIRED)
        self.assertTrue(order.delivery_offers.filter(
            rider=second, state=DeliveryOffer.State.OFFERED).exists())

    def test_the_offer_has_a_deadline(self):
        make_rider("r1")
        offer = offer_order(self._order())
        self.assertAlmostEqual(offer.seconds_left(), OFFER_TTL_SECONDS, delta=2)

    def test_only_one_live_offer_exists_at_a_time(self):
        make_rider("r1")
        order = self._order()
        offer_order(order)
        offer_order(order)
        offer_order(order)
        self.assertEqual(
            order.delivery_offers.filter(state=DeliveryOffer.State.OFFERED).count(), 1)

    def test_accepting_a_dead_offer_does_not_assign(self):
        """The race: the offer expired between the rider seeing it and tapping
        Accept. They must not be able to grab it."""
        make_rider("r1")
        order = self._order()
        offer = offer_order(order)
        DeliveryOffer.objects.filter(pk=offer.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1))
        offer.refresh_from_db()
        got, ok = accept_offer(offer)
        self.assertFalse(ok)
        self.assertIsNone(got.rider)

    def test_a_rider_cannot_accept_an_order_an_admin_already_gave_away(self):
        offered = make_rider("offered", km_away=0.5)
        chosen = make_rider("chosen", km_away=5)
        order = self._order()
        offer = offer_order(order)
        self.assertEqual(offer.rider, offered)

        assign_rider(order, chosen)   # admin override while the offer is live
        got, ok = accept_offer(offer)
        self.assertFalse(ok)
        self.assertEqual(got.rider, chosen)

    def test_admin_assign_closes_any_live_offer(self):
        make_rider("offered", km_away=0.5)
        chosen = make_rider("chosen", km_away=5)
        order = self._order()
        offer_order(order)
        assign_rider(order, chosen)
        self.assertFalse(order.delivery_offers.filter(state=DeliveryOffer.State.OFFERED).exists())

    def test_no_rider_online_leaves_the_order_for_the_admin_queue(self):
        make_rider("sleeping", available=False)
        order = self._order()
        self.assertIsNone(offer_order(order))
        self.assertEqual(order.delivery_offers.count(), 0)

    def test_sweep_offers_a_stuck_order_that_never_got_a_rider(self):
        """An order confirmed with nobody online gets picked up once a rider
        comes on, by the sweep — not left orphaned forever."""
        order = self._order()
        self.assertIsNone(offer_order(order))   # nobody online yet
        make_rider("late")
        expired, re_offered = sweep_offers()
        self.assertEqual(re_offered, 1)
        self.assertTrue(order.delivery_offers.filter(state=DeliveryOffer.State.OFFERED).exists())

    def test_a_cash_order_skips_the_offer_when_only_over_ceiling_riders_are_online(self):
        from food.models import DeliveryPricing
        cfg = DeliveryPricing.get_solo()
        cfg.rider_cash_ceiling = Decimal("100.00")
        cfg.save()
        rider = make_rider("maxed")
        # Give the rider a delivered COD order over the ceiling.
        from food.services_settlement import settle_order
        past = FoodOrder.objects.create(
            guest_name="G", guest_phone="017", delivery_address="A", restaurant=self.restaurant,
            rider=rider, subtotal=Decimal("500"), total=Decimal("500"),
            payment_method="COD", status=FoodOrder.Status.DELIVERED)
        settle_order(past)
        self.assertIsNone(offer_order(self._order(payment_method="COD")))


class RiderOfferApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.restaurant = Restaurant.objects.create(
            name="R", slug="r", status=Restaurant.Status.ACTIVE,
            pickup_lat=HERE[0], pickup_lng=HERE[1])
        self.rider = make_rider("r1")
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.rider.user).access_token}")

    def _order(self):
        return FoodOrder.objects.create(
            guest_name="G", guest_phone="017", delivery_address="Field 3",
            restaurant=self.restaurant, subtotal=Decimal("100"), total=Decimal("130"),
            delivery_fee=Decimal("30"), rider_base_pay=Decimal("35.00"), tip=Decimal("10"),
            status=FoodOrder.Status.CONFIRMED)

    def test_a_rider_sees_their_pending_offer(self):
        order = self._order()
        offer_order(order)
        d = self.client.get("/api/food/rider/offer/").json()["data"]["offer"]
        self.assertEqual(d["order_code"], order.order_code)
        self.assertEqual(d["restaurant_name"], "R")
        self.assertEqual(d["rider_pay"], "45.00")   # 35 base + 10 tip
        self.assertGreater(d["seconds_left"], 0)

    def test_no_offer_returns_null_not_an_error(self):
        res = self.client.get("/api/food/rider/offer/")
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(res.json()["data"]["offer"])

    def test_accepting_via_the_api_assigns_the_order(self):
        order = self._order()
        offer_order(order)
        res = self.client.post("/api/food/rider/offer/", {"action": "accept"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertTrue(res.json()["data"]["accepted"])
        order.refresh_from_db()
        self.assertEqual(order.rider, self.rider)

    def test_the_accepted_order_shows_up_in_the_riders_deliveries(self):
        offer_order(self._order())
        self.client.post("/api/food/rider/offer/", {"action": "accept"}, format="json")
        rows = self.client.get("/api/food/rider/orders/").json()["data"]
        self.assertEqual(len(rows), 1)

    def test_declining_via_the_api_frees_the_order(self):
        order = self._order()
        offer_order(order)
        res = self.client.post("/api/food/rider/offer/", {"action": "decline"}, format="json")
        self.assertEqual(res.status_code, 200)
        order.refresh_from_db()
        self.assertIsNone(order.rider)
        self.assertFalse(self.rider.delivery_offers.filter(
            state=DeliveryOffer.State.OFFERED).exists())

    def test_accepting_an_expired_offer_is_a_conflict(self):
        order = self._order()
        offer = offer_order(order)
        DeliveryOffer.objects.filter(pk=offer.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1))
        res = self.client.post("/api/food/rider/offer/", {"action": "accept"}, format="json")
        self.assertEqual(res.status_code, 409)
        order.refresh_from_db()
        self.assertIsNone(order.rider)

    def test_responding_with_no_offer_is_404(self):
        res = self.client.post("/api/food/rider/offer/", {"action": "accept"}, format="json")
        self.assertEqual(res.status_code, 404)

    def test_a_bad_action_is_400(self):
        offer_order(self._order())
        res = self.client.post("/api/food/rider/offer/", {"action": "maybe"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_the_offer_endpoint_is_rider_only(self):
        self.client.credentials()
        self.assertIn(self.client.get("/api/food/rider/offer/").status_code, (401, 403))


class TwoRidersRaceTests(TestCase):
    """Only one live offer exists at a time, so a straight double-accept cannot
    happen — but an admin override mid-offer is the real race, covered above.
    This pins that a declined cascade reaches a genuinely different rider."""

    def test_the_delivery_ends_up_with_exactly_one_rider(self):
        restaurant = Restaurant.objects.create(
            name="R", slug="r", status=Restaurant.Status.ACTIVE,
            pickup_lat=HERE[0], pickup_lng=HERE[1])
        r1 = make_rider("r1", km_away=0.5)
        r2 = make_rider("r2", km_away=3)
        order = FoodOrder.objects.create(
            guest_name="G", guest_phone="017", delivery_address="A", restaurant=restaurant,
            subtotal=Decimal("100"), total=Decimal("100"), status=FoodOrder.Status.CONFIRMED)

        first = offer_order(order)
        self.assertEqual(first.rider, r1)
        second = decline_offer(first)
        self.assertEqual(second.rider, r2)
        got, ok = accept_offer(second)
        self.assertTrue(ok)
        self.assertEqual(got.rider, r2)
        self.assertEqual(order.delivery_offers.filter(state=DeliveryOffer.State.ACCEPTED).count(), 1)
