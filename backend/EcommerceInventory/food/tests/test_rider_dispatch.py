from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from food.models import Restaurant, Rider, FoodOrder, DeliveryOffer
from food.services_dispatch import (dispatchable_riders, pick_rider_for, maybe_auto_assign_rider,
                                    offer_order)

User = get_user_model()

# Bancharampur upazila centre, near where real orders land.
BANCHARAMPUR = (Decimal("23.7104"), Decimal("90.9280"))


def make_rider(name, *, lat=None, lng=None, seen_minutes_ago=0, available=True):
    user = User.objects.create(username=f"u_{name}", email=f"{name}@x.com", role="Rider")
    return Rider.objects.create(
        user=user, name=name, is_available=available,
        current_lat=lat, current_lng=lng,
        last_seen_at=timezone.now() - timedelta(minutes=seen_minutes_ago),
    )


class DispatchableTests(TestCase):
    def test_excludes_offline_stale_and_locationless_riders(self):
        fresh = make_rider("fresh", lat=BANCHARAMPUR[0], lng=BANCHARAMPUR[1], seen_minutes_ago=1)
        make_rider("stale", lat=BANCHARAMPUR[0], lng=BANCHARAMPUR[1], seen_minutes_ago=10)
        make_rider("offline", lat=BANCHARAMPUR[0], lng=BANCHARAMPUR[1], available=False)
        make_rider("nogps", seen_minutes_ago=1)
        self.assertEqual(list(dispatchable_riders()), [fresh])


class PickRiderTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(
            name="R", slug="r", status=Restaurant.Status.ACTIVE,
            pickup_lat=BANCHARAMPUR[0], pickup_lng=BANCHARAMPUR[1],
        )
        self.order = FoodOrder.objects.create(
            guest_name="G", guest_phone="017", delivery_address="A",
            restaurant=self.restaurant, subtotal=Decimal("100"), total=Decimal("100"),
            status=FoodOrder.Status.CONFIRMED,
        )

    def test_picks_the_nearest_rider_to_the_restaurant(self):
        far = make_rider("far", lat=Decimal("23.8000"), lng=Decimal("91.0000"), seen_minutes_ago=1)
        near = make_rider("near", lat=Decimal("23.7110"), lng=Decimal("90.9285"), seen_minutes_ago=1)
        self.assertEqual(pick_rider_for(self.order), near)
        self.assertNotEqual(pick_rider_for(self.order), far)

    def test_falls_back_to_least_loaded_when_restaurant_has_no_pickup_point(self):
        self.restaurant.pickup_lat = None
        self.restaurant.pickup_lng = None
        self.restaurant.save()
        busy = make_rider("busy", lat=BANCHARAMPUR[0], lng=BANCHARAMPUR[1], seen_minutes_ago=1)
        idle = make_rider("idle", lat=BANCHARAMPUR[0], lng=BANCHARAMPUR[1], seen_minutes_ago=2)
        FoodOrder.objects.create(
            guest_name="G2", guest_phone="018", delivery_address="B",
            restaurant=self.restaurant, subtotal=Decimal("50"), total=Decimal("50"),
            status=FoodOrder.Status.OUT_FOR_DELIVERY, rider=busy,
        )
        self.assertEqual(pick_rider_for(self.order), idle)

    def test_returns_none_when_nobody_is_dispatchable(self):
        self.assertIsNone(pick_rider_for(self.order))


class AutoAssignTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(
            name="R", slug="r", status=Restaurant.Status.ACTIVE,
            pickup_lat=BANCHARAMPUR[0], pickup_lng=BANCHARAMPUR[1],
        )

    def _order(self, status=FoodOrder.Status.CONFIRMED, rider=None):
        return FoodOrder.objects.create(
            guest_name="G", guest_phone="017", delivery_address="A",
            restaurant=self.restaurant, subtotal=Decimal("100"), total=Decimal("100"),
            status=status, rider=rider,
        )

    def test_offers_on_confirmed_rather_than_assigning(self):
        """A confirmed order is *offered*, not silently handed over — the rider
        is not attached until they accept."""
        rider = make_rider("r1", lat=BANCHARAMPUR[0], lng=BANCHARAMPUR[1], seen_minutes_ago=1)
        order = self._order()
        offer = maybe_auto_assign_rider(order)
        self.assertEqual(offer.rider, rider)
        self.assertEqual(offer.state, DeliveryOffer.State.OFFERED)
        order.refresh_from_db()
        self.assertIsNone(order.rider)   # not yet — the rider must accept

    def test_does_not_re_offer_an_order_that_already_has_a_rider(self):
        first = make_rider("r1", lat=BANCHARAMPUR[0], lng=BANCHARAMPUR[1], seen_minutes_ago=1)
        make_rider("r2", lat=BANCHARAMPUR[0], lng=BANCHARAMPUR[1], seen_minutes_ago=1)
        order = self._order(rider=first)
        self.assertIsNone(maybe_auto_assign_rider(order))

    def test_does_not_double_offer_a_live_offer(self):
        make_rider("r1", lat=BANCHARAMPUR[0], lng=BANCHARAMPUR[1], seen_minutes_ago=1)
        order = self._order()
        first = offer_order(order)
        again = offer_order(order)
        self.assertEqual(first.id, again.id)
        self.assertEqual(order.delivery_offers.count(), 1)

    def test_ignores_orders_not_yet_confirmed(self):
        make_rider("r1", lat=BANCHARAMPUR[0], lng=BANCHARAMPUR[1], seen_minutes_ago=1)
        order = self._order(status=FoodOrder.Status.PLACED)
        self.assertIsNone(maybe_auto_assign_rider(order))
        self.assertEqual(order.delivery_offers.count(), 0)

    def test_notifies_the_offered_rider(self):
        rider = make_rider("r1", lat=BANCHARAMPUR[0], lng=BANCHARAMPUR[1], seen_minutes_ago=1)
        order = self._order()
        maybe_auto_assign_rider(order)
        self.assertTrue(rider.user.food_notifications.filter(order_code=order.order_code).exists())


class ConfirmOffersRiderTests(TestCase):
    def test_admin_confirming_an_order_offers_it(self):
        admin = User.objects.create(username="adm", email="adm@x.com", role="Admin")
        restaurant = Restaurant.objects.create(
            name="R", slug="r", status=Restaurant.Status.ACTIVE,
            pickup_lat=BANCHARAMPUR[0], pickup_lng=BANCHARAMPUR[1],
        )
        rider = make_rider("r1", lat=BANCHARAMPUR[0], lng=BANCHARAMPUR[1], seen_minutes_ago=1)
        order = FoodOrder.objects.create(
            guest_name="G", guest_phone="017", delivery_address="A",
            restaurant=restaurant, subtotal=Decimal("100"), total=Decimal("100"),
            status=FoodOrder.Status.PLACED,
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(admin).access_token}")
        res = client.patch(f"/api/food/admin/orders/{order.id}/status/",
                           {"status": "CONFIRMED"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        order.refresh_from_db()
        self.assertIsNone(order.rider)
        self.assertTrue(order.delivery_offers.filter(
            rider=rider, state=DeliveryOffer.State.OFFERED).exists())
