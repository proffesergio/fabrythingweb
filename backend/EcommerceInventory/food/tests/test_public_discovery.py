"""Homepage discovery rows and the Browse page.

Three query shapes share PublicRestaurantListView:
  nearest  — ?zone=&lat=&lng=&sort=distance
  also-like— ?zone=&sort=popular&exclude=<ids from the nearest row>
  browse   — ?all=true  (every restaurant; `zone` only marks deliverability)
"""
from decimal import Decimal

from django.test import TestCase

from food.models import DeliveryZone, FoodOrder, Restaurant, RestaurantZone


def restaurant(name, lat=None, lng=None, **kw):
    return Restaurant.objects.create(
        name=name, slug=name.lower().replace(" ", "-"),
        status=Restaurant.Status.ACTIVE,
        pickup_lat=Decimal(str(lat)) if lat is not None else None,
        pickup_lng=Decimal(str(lng)) if lng is not None else None,
        **kw)


def rows(res):
    # CommonListAPIMixin nests the page: {"data": {"data": [...]}}.
    return res.json()["data"]["data"]


class NearestRowTests(TestCase):
    def setUp(self):
        self.zone = DeliveryZone.objects.create(
            name="Sadar", center_lat=Decimal("23.7500"), center_lng=Decimal("90.7800"),
            radius_km=Decimal("10"))
        # Roughly 1km, 5km and 12km north of the pin at (23.75, 90.78).
        self.near = restaurant("Near Kitchen", 23.7590, 90.7800)
        self.mid = restaurant("Mid Kitchen", 23.7950, 90.7800)
        self.far = restaurant("Far Kitchen", 23.8580, 90.7800)
        for r in (self.near, self.mid, self.far):
            RestaurantZone.objects.create(restaurant=r, zone=self.zone)

    def test_sorts_by_real_distance_from_the_pin(self):
        res = self.client.get(f"/api/food/restaurants/?zone={self.zone.id}"
                              "&lat=23.75&lng=90.78&sort=distance")
        self.assertEqual(res.status_code, 200)
        self.assertEqual([r["name"] for r in rows(res)],
                         ["Near Kitchen", "Mid Kitchen", "Far Kitchen"])

    def test_reports_the_distance(self):
        res = self.client.get(f"/api/food/restaurants/?zone={self.zone.id}"
                              "&lat=23.75&lng=90.78&sort=distance")
        first = rows(res)[0]
        self.assertIsNotNone(first["distance_km"])
        self.assertLess(first["distance_km"], 2)

    def test_restaurants_without_a_pin_sort_last(self):
        pinless = restaurant("No Pin Kitchen")
        RestaurantZone.objects.create(restaurant=pinless, zone=self.zone)
        res = self.client.get(f"/api/food/restaurants/?zone={self.zone.id}"
                              "&lat=23.75&lng=90.78&sort=distance")
        result = rows(res)
        self.assertEqual(result[-1]["name"], "No Pin Kitchen")
        self.assertIsNone(result[-1]["distance_km"])

    def test_bad_coordinates_do_not_500(self):
        res = self.client.get(f"/api/food/restaurants/?zone={self.zone.id}"
                              "&lat=abc&lng=xyz&sort=distance")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(rows(res)), 3)

    def test_without_coordinates_it_still_returns_the_zone(self):
        res = self.client.get(f"/api/food/restaurants/?zone={self.zone.id}&sort=distance")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(rows(res)), 3)


class AlsoLikeRowTests(TestCase):
    def setUp(self):
        self.zone = DeliveryZone.objects.create(
            name="Sadar", center_lat=Decimal("23.75"), center_lng=Decimal("90.78"))
        self.a = restaurant("Popular Place")
        self.b = restaurant("Quiet Place")
        for r in (self.a, self.b):
            RestaurantZone.objects.create(restaurant=r, zone=self.zone)

        for i in range(3):
            FoodOrder.objects.create(
                guest_name="G", guest_phone="017", delivery_address="a", restaurant=self.a,
                subtotal=Decimal("100"), total=Decimal("100"),
                status=FoodOrder.Status.DELIVERED)
        # Cancelled orders must not count as popularity.
        for i in range(9):
            FoodOrder.objects.create(
                guest_name="G", guest_phone="017", delivery_address="a", restaurant=self.b,
                subtotal=Decimal("100"), total=Decimal("100"),
                status=FoodOrder.Status.CANCELLED)

    def test_orders_by_delivered_count(self):
        res = self.client.get(f"/api/food/restaurants/?zone={self.zone.id}&sort=popular")
        self.assertEqual([r["name"] for r in rows(res)], ["Popular Place", "Quiet Place"])

    def test_excludes_ids_already_shown(self):
        res = self.client.get(f"/api/food/restaurants/?zone={self.zone.id}"
                              f"&sort=popular&exclude={self.a.id}")
        names = [r["name"] for r in rows(res)]
        self.assertNotIn("Popular Place", names)
        self.assertIn("Quiet Place", names)

    def test_junk_in_exclude_is_ignored(self):
        res = self.client.get(f"/api/food/restaurants/?zone={self.zone.id}"
                              "&sort=popular&exclude=abc,,%20")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(rows(res)), 2)


class BrowseAllTests(TestCase):
    def setUp(self):
        self.mine = DeliveryZone.objects.create(
            name="Mine", center_lat=Decimal("23.75"), center_lng=Decimal("90.78"))
        self.other = DeliveryZone.objects.create(
            name="Other", center_lat=Decimal("23.90"), center_lng=Decimal("90.90"))
        self.here = restaurant("Delivers Here")
        self.there = restaurant("Delivers Elsewhere")
        RestaurantZone.objects.create(restaurant=self.here, zone=self.mine)
        RestaurantZone.objects.create(restaurant=self.there, zone=self.other)

    def test_all_true_returns_every_restaurant(self):
        res = self.client.get(f"/api/food/restaurants/?all=true&zone={self.mine.id}")
        self.assertEqual(len(rows(res)), 2)

    def test_all_true_marks_which_ones_deliver_to_you(self):
        res = self.client.get(f"/api/food/restaurants/?all=true&zone={self.mine.id}")
        by_name = {r["name"]: r for r in rows(res)}
        self.assertTrue(by_name["Delivers Here"]["delivers_to_zone"])
        self.assertFalse(by_name["Delivers Elsewhere"]["delivers_to_zone"])

    def test_without_all_the_zone_still_filters(self):
        res = self.client.get(f"/api/food/restaurants/?zone={self.mine.id}")
        self.assertEqual([r["name"] for r in rows(res)], ["Delivers Here"])

    def test_browse_still_honours_search(self):
        res = self.client.get("/api/food/restaurants/?all=true&search=Elsewhere")
        self.assertEqual([r["name"] for r in rows(res)], ["Delivers Elsewhere"])

    def test_inactive_restaurants_are_never_listed(self):
        restaurant("Suspended Co").__class__.objects.filter(name="Suspended Co").update(
            status=Restaurant.Status.SUSPENDED)
        res = self.client.get("/api/food/restaurants/?all=true")
        self.assertNotIn("Suspended Co", [r["name"] for r in rows(res)])
