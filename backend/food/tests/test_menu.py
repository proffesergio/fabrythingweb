from decimal import Decimal
from django.test import TestCase
from food.models import Restaurant, FoodCategory, FoodItem


class MenuTests(TestCase):
    def setUp(self):
        self.r = Restaurant.objects.create(name="R", slug="r", status=Restaurant.Status.ACTIVE)
        self.c = FoodCategory.objects.create(restaurant=self.r, name="Rice", display_order=1)

    def test_effective_price_prefers_discount(self):
        item = FoodItem.objects.create(
            restaurant=self.r, category_id=self.c, name="Biriyani", slug="biriyani",
            price=Decimal("250.00"), discount_price=Decimal("200.00"),
        )
        self.assertEqual(item.effective_price, Decimal("200.00"))

    def test_effective_price_falls_back_to_price(self):
        item = FoodItem.objects.create(
            restaurant=self.r, category_id=self.c, name="Polao", slug="polao",
            price=Decimal("180.00"),
        )
        self.assertEqual(item.effective_price, Decimal("180.00"))
