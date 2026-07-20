from django.test import TestCase
from django.core.management import call_command
from accounts.models import Modules


class UnifiedModuleSeederTests(TestCase):
    """seed_admin_modules is the single source of truth for the whole admin nav
    (ecommerce + food + customers). It must register everything and must NOT delete
    the food modules (the old landmine)."""

    def test_registers_full_platform_nav_idempotently(self):
        call_command("seed_admin_modules")
        call_command("seed_admin_modules")  # idempotent

        # Ecommerce parents
        for name in ["Dashboard", "Products", "Orders", "Inventory", "Settings"]:
            self.assertTrue(Modules.objects.filter(module_name=name, is_active=True).exists(), name)

        # Food group now lives in the SAME seeder
        food = Modules.objects.get(module_name="Food")
        self.assertIsNone(food.parent_id)
        for name, url in [
            ("Food Dashboard", "/manage/food/dashboard"),
            ("Restaurants", "/manage/food/restaurants"),
            ("Menu Management", "/manage/food/menu"),
            ("Food Orders", "/manage/food/orders"),
            ("Delivery Zones", "/manage/food/zones"),
        ]:
            m = Modules.objects.get(module_name=name)
            self.assertEqual(m.module_url, url)
            self.assertEqual(m.parent_id, food)

        # New Customers module
        self.assertTrue(Modules.objects.filter(module_name="Customers", module_url="/manage/customers").exists())

        # No duplicate "Food" after re-run
        self.assertEqual(Modules.objects.filter(module_name="Food").count(), 1)

    def test_does_not_delete_food_modules_when_run_after_food_seeder(self):
        # Simulate the old landmine order: food seeder first, then admin seeder.
        call_command("seed_food_modules")
        call_command("seed_admin_modules")
        self.assertTrue(Modules.objects.filter(module_name="Restaurants", is_active=True).exists())
        self.assertTrue(Modules.objects.filter(module_name="Food", is_active=True).exists())
