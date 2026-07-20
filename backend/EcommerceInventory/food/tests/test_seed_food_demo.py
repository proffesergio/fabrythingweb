from django.test import TestCase
from django.core.management import call_command
from food.models import Restaurant, FoodItem, DeliveryZone


class SeedFoodDemoTests(TestCase):
    def test_creates_active_restaurants_with_menus_idempotently(self):
        call_command("seed_food_demo")
        call_command("seed_food_demo")  # second run must not duplicate

        self.assertGreaterEqual(Restaurant.objects.filter(status=Restaurant.Status.ACTIVE).count(), 1)
        self.assertGreaterEqual(DeliveryZone.objects.filter(is_active=True).count(), 1)

        r = Restaurant.objects.get(slug="star-kitchen")
        self.assertEqual(r.status, Restaurant.Status.ACTIVE)
        self.assertTrue(r.items.exists())
        self.assertTrue(r.hours.exists())
        self.assertTrue(r.zones.exists())

        # Idempotent: exactly the two seed restaurants, no duplicate items.
        self.assertEqual(Restaurant.objects.count(), 2)
        first_count = FoodItem.objects.count()
        call_command("seed_food_demo")
        self.assertEqual(FoodItem.objects.count(), first_count)
