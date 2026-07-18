from decimal import Decimal
from django.test import TestCase
from food.models import Restaurant, FoodCategory, FoodItem
from food.serializers import RestaurantDetailSerializer
from food.i18n import localized


class I18nTests(TestCase):
    def test_bn_fallback_to_en(self):
        r = Restaurant(name="Rahim", name_bn="")
        self.assertEqual(localized(r, "name", "bn"), "Rahim")

    def test_bn_used_when_present(self):
        r = Restaurant(name="Rahim", name_bn="রহিম")
        self.assertEqual(localized(r, "name", "bn"), "রহিম")


class RestaurantDetailSerializerTests(TestCase):
    def setUp(self):
        self.r = Restaurant.objects.create(name="Rahim", name_bn="রহিম", slug="rahim",
                                           status=Restaurant.Status.ACTIVE)
        c = FoodCategory.objects.create(restaurant=self.r, name="Rice")
        FoodItem.objects.create(restaurant=self.r, category_id=c, name="Biriyani",
                                slug="biriyani", price=Decimal("250"), is_available=True)
        FoodItem.objects.create(restaurant=self.r, category_id=c, name="Hidden",
                                slug="hidden", price=Decimal("100"), is_available=False)

    def test_detail_includes_only_available_items(self):
        data = RestaurantDetailSerializer(self.r, context={"lang": "en"}).data
        names = [i["name"] for cat in data["categories"] for i in cat["items"]]
        self.assertIn("Biriyani", names)
        self.assertNotIn("Hidden", names)

    def test_bn_name_rendered(self):
        data = RestaurantDetailSerializer(self.r, context={"lang": "bn"}).data
        self.assertEqual(data["name"], "রহিম")
