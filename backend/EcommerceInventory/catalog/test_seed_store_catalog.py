from django.core.management import call_command
from django.test import TestCase

from accounts.models import Users
from catalog.models import Categories


class SeedStoreCatalogCategoryTests(TestCase):
    def setUp(self):
        self.owner = Users.objects.create_user(
            username="root", email="root@x.com", password="x",
            role="Super Admin", country="Bangladesh")

    def test_creates_tree(self):
        call_command("seed_store_catalog", "--categories-only")
        fashion = Categories.objects.get(slug="fashion")
        men = Categories.objects.get(slug="fashion-men")
        self.assertEqual(men.parent_id_id, fashion.id)
        self.assertTrue(Categories.objects.filter(slug="phones").exists())
        self.assertTrue(Categories.objects.filter(slug="computers-laptops").exists())
        self.assertTrue(Categories.objects.filter(slug="gadgets-smart-watches").exists())

    def test_idempotent_and_preserves_admin_edits(self):
        call_command("seed_store_catalog", "--categories-only")
        n = Categories.objects.count()
        cat = Categories.objects.get(slug="phones")
        cat.name = "Phones & Tabs"
        cat.save()
        call_command("seed_store_catalog", "--categories-only")
        self.assertEqual(Categories.objects.count(), n)
        cat.refresh_from_db()
        self.assertEqual(cat.name, "Phones & Tabs", "re-run clobbered an admin edit")

    def test_reparents_legacy_fashion_categories(self):
        legacy = Categories.objects.create(
            name="Men's Fashion", slug="mens-fashion", description="legacy",
            domain_user_id=self.owner, added_by_user_id=self.owner)
        call_command("seed_store_catalog", "--categories-only")
        legacy.refresh_from_db()
        self.assertEqual(legacy.parent_id_id, Categories.objects.get(slug="fashion").id)
        # fashion-men must NOT be created as a duplicate when mens-fashion was adopted
        self.assertFalse(Categories.objects.filter(slug="fashion-men").exists())

    def test_rerun_preserves_admin_rename_of_adopted_category(self):
        Categories.objects.create(
            name="Men's Fashion", slug="mens-fashion", description="legacy",
            domain_user_id=self.owner, added_by_user_id=self.owner)
        call_command("seed_store_catalog", "--categories-only")
        adopted = Categories.objects.get(slug="mens-fashion")
        fashion_id = Categories.objects.get(slug="fashion").id
        self.assertEqual(adopted.parent_id_id, fashion_id)   # adoption happened
        adopted.name = "Menswear (admin renamed)"
        adopted.save()
        call_command("seed_store_catalog", "--categories-only")
        adopted.refresh_from_db()
        self.assertEqual(adopted.name, "Menswear (admin renamed)",
                         "re-run clobbered an admin rename of an adopted category")
        self.assertEqual(adopted.parent_id_id, fashion_id,
                         "re-run must keep the structural parent")

    def test_force_update_resyncs_adopted_category(self):
        Categories.objects.create(
            name="Men's Fashion", slug="mens-fashion", description="legacy",
            domain_user_id=self.owner, added_by_user_id=self.owner)
        call_command("seed_store_catalog", "--categories-only")
        adopted = Categories.objects.get(slug="mens-fashion")
        adopted.name = "Menswear (admin renamed)"
        adopted.save()
        call_command("seed_store_catalog", "--categories-only", "--force-update")
        adopted.refresh_from_db()
        self.assertEqual(adopted.name, "Men",
                         "--force-update must be able to resync an adopted category's name")
