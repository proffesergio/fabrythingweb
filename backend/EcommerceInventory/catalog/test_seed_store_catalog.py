import json
import os
import shutil
import tempfile
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from accounts.models import Users
from catalog.models import Categories, Products, ProductVariant


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


class SeedStoreCatalogProductTests(TestCase):
    def setUp(self):
        self.owner = Users.objects.create_user(
            username="root2", email="root2@x.com", password="x",
            role="Super Admin", country="Bangladesh")

    def _run(self):
        # never hit network or real storage in tests
        with patch("catalog.management.commands.seed_store_catalog.Command._import_image",
                   return_value="https://cdn.test/x.jpg"):
            call_command("seed_store_catalog")

    def test_seeds_products_with_variants_and_owner(self):
        self._run()
        self.assertGreater(Products.objects.count(), 0)
        self.assertEqual(Products.objects.filter(domain_user_id__isnull=True).count(), 0)
        for p in Products.objects.all():
            self.assertTrue(p.variants.filter(is_active=True).exists(),
                            f"{p.slug} has no sellable variant")

    def test_partner_products_carry_source_url(self):
        # potakait.json / canvasit.json (the actual partner fixtures) are not
        # committed yet — Task 6 is still pending — so this cannot assert
        # against the real fixture directory the way the brief sketched it
        # (that would fail today with zero partner rows, through no fault of
        # the seeding code). Point FIXTURE_DIR at a temp dir holding one
        # synthetic partner-style entry instead, so this proves the real
        # source_url/source_price/price_synced_at flow-through end to end
        # without depending on, or fabricating, a committed partner fixture.
        tmpdir = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmpdir, "partner_probe.json"), "w", encoding="utf-8") as fh:
                json.dump([{
                    "category_path": "men-tshirts",
                    "name": "Partner Probe Tee",
                    "price": 500.0,
                    "source_url": "https://partner.example.com/p/1",
                    "images": ["https://partner.example.com/img.jpg"],
                }], fh)
            with patch("catalog.management.commands.seed_store_catalog.FIXTURE_DIR", tmpdir):
                self._run()
            self.assertTrue(Products.objects.exclude(source_url="").exists())
        finally:
            shutil.rmtree(tmpdir)

    def test_force_update_refreshes_existing_variant_price(self):
        # CRITICAL: ProductVariant.objects.get_or_create(...) only applies
        # `defaults` on creation, so a forced re-seed used to never update an
        # existing variant's price -- checkout would keep charging the
        # seed-time price forever, no matter how many times --force-update
        # ran with a new fixture price. This must fail against the current
        # get_or_create-without-update implementation.
        tmpdir = tempfile.mkdtemp()
        try:
            fixture_path = os.path.join(tmpdir, "partner_probe.json")
            with open(fixture_path, "w", encoding="utf-8") as fh:
                json.dump([{
                    "category_path": "men-tshirts",
                    "name": "Partner Probe Tee Force",
                    "price": 500.0,
                    "source_url": "https://partner.example.com/p/3",
                    "images": ["https://partner.example.com/img.jpg"],
                }], fh)
            with patch("catalog.management.commands.seed_store_catalog.FIXTURE_DIR", tmpdir):
                self._run()
                p = Products.objects.get(slug="partner-probe-tee-force")
                variant = p.variants.get()
                # seed_product_entry stores the fixture price as base_price
                # and marks the variant up (apply_markup: floor=50/3% by
                # default -- 3% of 500 is 15, below the floor).
                self.assertEqual(variant.price, 550.0)

                with open(fixture_path, "w", encoding="utf-8") as fh:
                    json.dump([{
                        "category_path": "men-tshirts",
                        "name": "Partner Probe Tee Force",
                        "price": 750.0,
                        "source_url": "https://partner.example.com/p/3",
                        "images": ["https://partner.example.com/img.jpg"],
                    }], fh)
                with patch("catalog.management.commands.seed_store_catalog.Command._import_image",
                           return_value="https://cdn.test/x.jpg"):
                    call_command("seed_store_catalog", "--force-update")
            variant.refresh_from_db()
            # 3% of 750 is 22.5, still below the 50 floor.
            self.assertEqual(variant.price, 800.0,
                              "--force-update must refresh an existing variant's price")
        finally:
            shutil.rmtree(tmpdir)

    def test_rerun_preserves_admin_price_edit(self):
        # Same reasoning as test_partner_products_carry_source_url: use a
        # synthetic partner entry so a source_url-carrying product actually
        # exists to edit, without depending on the not-yet-committed partner
        # fixtures. This genuinely fails against an update_or_create-style
        # (clobbering) implementation, which would reset the price back to
        # 500 on the second run.
        tmpdir = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmpdir, "partner_probe.json"), "w", encoding="utf-8") as fh:
                json.dump([{
                    "category_path": "men-tshirts",
                    "name": "Partner Probe Tee Rerun",
                    "price": 500.0,
                    "source_url": "https://partner.example.com/p/2",
                    "images": ["https://partner.example.com/img.jpg"],
                }], fh)
            with patch("catalog.management.commands.seed_store_catalog.FIXTURE_DIR", tmpdir):
                self._run()
                p = Products.objects.exclude(source_url="").first()
                self.assertIsNotNone(p)
                p.initial_selling_price = 12345
                p.save()
                self._run()
            p.refresh_from_db()
            self.assertEqual(p.initial_selling_price, 12345)
        finally:
            shutil.rmtree(tmpdir)
