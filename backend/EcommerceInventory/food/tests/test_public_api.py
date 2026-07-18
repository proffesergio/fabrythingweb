from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from food.models import Restaurant, FoodCategory, FoodItem


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
        with self.assertNumQueries(4):
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

        with self.assertNumQueries(4):
            self.client.get("/api/food/restaurants/active/")

        with self.assertNumQueries(4):
            self.client.get("/api/food/restaurants/big/")

    def test_detail_404_for_non_active_slug(self):
        res = self.client.get("/api/food/restaurants/pending/")
        self.assertEqual(res.status_code, 404)

    def test_detail_404_for_unknown_slug(self):
        res = self.client.get("/api/food/restaurants/does-not-exist/")
        self.assertEqual(res.status_code, 404)
