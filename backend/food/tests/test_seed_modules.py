from django.test import TestCase
from django.core.management import call_command
from accounts.models import Modules


class SeedFoodModulesTests(TestCase):
    def test_idempotent_and_creates_food_menu(self):
        """Test that seed_food_modules is idempotent and creates correct modules."""
        # Run command once
        call_command("seed_food_modules")

        # Run command again — must not duplicate
        call_command("seed_food_modules")

        # Verify exactly one "Food" module
        self.assertEqual(Modules.objects.filter(module_name="Food").count(), 1)

        # Verify the Restaurants child module exists with correct URL
        self.assertTrue(Modules.objects.filter(module_url="/manage/food/restaurants").exists())

        # Verify the Delivery Zones child module exists with correct URL
        self.assertTrue(Modules.objects.filter(module_url="/manage/food/zones").exists())

        # Verify Food module has no parent
        food_module = Modules.objects.get(module_name="Food")
        self.assertIsNone(food_module.parent_id)

        # Verify child modules have Food as parent
        restaurants = Modules.objects.get(module_name="Restaurants")
        self.assertEqual(restaurants.parent_id, food_module)

        delivery_zones = Modules.objects.get(module_name="Delivery Zones")
        self.assertEqual(delivery_zones.parent_id, food_module)

        # New production admin modules register under Food
        for name, url in [
            ("Food Dashboard", "/manage/food/dashboard"),
            ("Food Orders", "/manage/food/orders"),
            ("Menu Management", "/manage/food/menu"),
        ]:
            mod = Modules.objects.get(module_name=name)
            self.assertEqual(mod.module_url, url)
            self.assertEqual(mod.parent_id, food_module)
