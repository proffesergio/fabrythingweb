from datetime import time
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from food.models import (Restaurant, FoodCategory, FoodItem, DeliveryZone, RestaurantZone,
                         RestaurantHours)
from food.services import served_zones


class PublicApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.active = Restaurant.objects.create(name="Active", slug="active", status=Restaurant.Status.ACTIVE)
        self.pending = Restaurant.objects.create(name="Pending", slug="pending", status=Restaurant.Status.PENDING)
        c = FoodCategory.objects.create(restaurant=self.active, name="Rice")
        for i in range(5):
            FoodItem.objects.create(restaurant=self.active, category_id=c, name=f"Item{i}",
                                    slug=f"item{i}", price=Decimal("100"), is_available=True)

    def test_list_hides_non_active(self):
        res = self.client.get("/api/food/restaurants/")
        self.assertEqual(res.status_code, 200)
        slugs = [r["slug"] for r in res.json()["data"]["data"]]
        self.assertIn("active", slugs)
        self.assertNotIn("pending", slugs)

    def test_detail_is_query_bounded(self):
        # Detail must not scale queries with item count (no N+1).
        # 6 = restaurant + categories + items + option groups + zones + hours.
        # `zones` feeds served_zone_ids and `hours` feeds is_open_now; both are
        # prefetched precisely so this stays flat as the menu grows.
        with self.assertNumQueries(6):
            self.client.get("/api/food/restaurants/active/")

    def test_detail_query_count_invariant_under_more_items(self):
        # A second restaurant with ~20 items must yield the SAME query count
        # as the one with 5 items above — proves the count doesn't scale with
        # item count (no N+1).
        big = Restaurant.objects.create(name="Big", slug="big", status=Restaurant.Status.ACTIVE)
        c2 = FoodCategory.objects.create(restaurant=big, name="Mains")
        for i in range(20):
            FoodItem.objects.create(restaurant=big, category_id=c2, name=f"BigItem{i}",
                                    slug=f"bigitem{i}", price=Decimal("100"), is_available=True)

        with self.assertNumQueries(6):
            self.client.get("/api/food/restaurants/active/")

        with self.assertNumQueries(6):
            self.client.get("/api/food/restaurants/big/")

    def _row(self, slug="active"):
        rows = self.client.get("/api/food/restaurants/").json()["data"]["data"]
        return next(r for r in rows if r["slug"] == slug)

    def test_is_open_now_follows_the_hours_not_the_master_switch(self):
        """The card must not say "Open now" when checkout would reject the order.

        `is_open` is only the owner's master switch; the schedule lives in
        RestaurantHours. Serializing the raw column made every restaurant look
        open around the clock while place_food_cod_order rejected them as closed.
        """
        self.assertTrue(self.active.is_open)          # master switch on…
        self.assertFalse(self._row()["is_open_now"])  # …but no hours: closed.

        now = timezone.localtime()
        RestaurantHours.objects.create(restaurant=self.active, weekday=now.weekday(),
                                       open_time=time(0, 0), close_time=time(23, 59))
        self.assertTrue(self._row()["is_open_now"])

    def test_is_open_now_is_false_when_the_master_switch_is_off(self):
        now = timezone.localtime()
        RestaurantHours.objects.create(restaurant=self.active, weekday=now.weekday(),
                                       open_time=time(0, 0), close_time=time(23, 59))
        Restaurant.objects.filter(pk=self.active.pk).update(is_open=False)
        self.assertFalse(self._row()["is_open_now"])

    def test_is_open_now_does_not_add_a_query_per_restaurant(self):
        """is_currently_open filters hours in Python precisely so the prefetch
        works — a .filter() call here would be an N+1 across the whole list."""
        now = timezone.localtime()
        for i in range(6):
            r = Restaurant.objects.create(name=f"R{i}", slug=f"r{i}",
                                          status=Restaurant.Status.ACTIVE)
            RestaurantHours.objects.create(restaurant=r, weekday=now.weekday(),
                                           open_time=time(0, 0), close_time=time(23, 59))
        with self.assertNumQueries(3):  # count + page + hours prefetch
            self.client.get("/api/food/restaurants/")

    def _served_ids(self, slug="active"):
        return self.client.get(f"/api/food/restaurants/{slug}/").json()["data"]["served_zone_ids"]

    def test_served_zone_ids_is_null_when_unconfigured(self):
        """null tells the client "offer every area" — the restaurant delivers
        everywhere until an admin assigns zones."""
        DeliveryZone.objects.create(name="Z1", center_lat="23.8", center_lng="90.4", radius_km="5")
        self.assertIsNone(self._served_ids())

    def test_served_zone_ids_matches_the_checkout_allow_list(self):
        """The dropdown and the order endpoint must never disagree — offering an
        area that place_food_cod_order then rejects is what produced the opaque
        "Could not place order" 400."""
        z1 = DeliveryZone.objects.create(name="Z1", center_lat="23.8", center_lng="90.4", radius_km="5")
        DeliveryZone.objects.create(name="Z2", center_lat="10", center_lng="10", radius_km="1")
        RestaurantZone.objects.create(restaurant=self.active, zone=z1)

        self.assertEqual(self._served_ids(), [z1.id])
        self.assertEqual(set(self._served_ids()),
                         set(served_zones(self.active).values_list("id", flat=True)))

    def test_served_zone_ids_omits_inactive_zones(self):
        z1 = DeliveryZone.objects.create(name="Z1", center_lat="23.8", center_lng="90.4", radius_km="5")
        dead = DeliveryZone.objects.create(name="Dead", center_lat="10", center_lng="10",
                                           radius_km="1", is_active=False)
        RestaurantZone.objects.create(restaurant=self.active, zone=z1)
        RestaurantZone.objects.create(restaurant=self.active, zone=dead)
        self.assertEqual(self._served_ids(), [z1.id])

    def test_detail_404_for_non_active_slug(self):
        res = self.client.get("/api/food/restaurants/pending/")
        self.assertEqual(res.status_code, 404)

    def test_detail_404_for_unknown_slug(self):
        res = self.client.get("/api/food/restaurants/does-not-exist/")
        self.assertEqual(res.status_code, 404)
