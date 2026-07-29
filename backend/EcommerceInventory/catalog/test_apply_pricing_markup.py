"""Retroactive backfill: apply_pricing_markup.

Dry run by default, --apply to write, following purge_demo_catalog /
prune_orphan_logins house style. See catalog/management/commands/
apply_pricing_markup.py for the rule.
"""
from django.core.management import call_command
from django.test import TestCase
from io import StringIO

from accounts.models import Users
from catalog.models import Categories, Products, ProductVariant
from catalog.pricing import apply_markup


def _run(*args):
    out = StringIO()
    call_command("apply_pricing_markup", *args, stdout=out)
    return out.getvalue()


class ApplyPricingMarkupTests(TestCase):
    def setUp(self):
        self.owner = Users.objects.create_user(
            username="root", email="root@x.com", password="x",
            role="Super Admin", country="Bangladesh")
        self.cat = Categories.objects.create(name="Shirts", slug="apm-shirts", description="")
        self.cheap = Products.objects.create(
            name="Cheap Tee", slug="apm-cheap-tee", sku="APM-0001", category_id=self.cat,
            description="", initial_buying_price=50, initial_selling_price=99,
            domain_user_id=self.owner, added_by_user_id=self.owner)
        self.cheap_variant = ProductVariant.objects.create(
            product=self.cheap, sku="APM-0001-DEF", price=99, stock_quantity=10)

        self.expensive = Products.objects.create(
            name="Gaming Laptop", slug="apm-laptop", sku="APM-0002", category_id=self.cat,
            description="", initial_buying_price=800000, initial_selling_price=989900,
            discount_price=950000,
            domain_user_id=self.owner, added_by_user_id=self.owner)
        self.expensive_variant = ProductVariant.objects.create(
            product=self.expensive, sku="APM-0002-DEF", price=989900,
            discount_price=950000, stock_quantity=3)

    def test_dry_run_writes_nothing(self):
        _run()
        self.cheap.refresh_from_db()
        self.expensive.refresh_from_db()
        self.assertIsNone(self.cheap.base_price)
        self.assertEqual(self.cheap.initial_selling_price, 99)
        self.assertIsNone(self.expensive.base_price)
        self.assertEqual(self.expensive.initial_selling_price, 989900)

    def test_apply_sets_base_price_and_marks_up_a_cheap_item(self):
        _run("--apply")
        self.cheap.refresh_from_db()
        self.assertEqual(self.cheap.base_price, 99)
        self.assertEqual(self.cheap.initial_selling_price, apply_markup(99))
        self.assertEqual(self.cheap.initial_selling_price, 149.0)  # floor wins

    def test_apply_marks_up_an_expensive_item_by_percentage(self):
        _run("--apply")
        self.expensive.refresh_from_db()
        self.assertEqual(self.expensive.base_price, 989900)
        self.assertEqual(self.expensive.initial_selling_price, apply_markup(989900))
        self.assertEqual(self.expensive.discount_price, apply_markup(950000))

    def test_apply_updates_active_variants_to_match(self):
        _run("--apply")
        self.cheap_variant.refresh_from_db()
        self.expensive_variant.refresh_from_db()
        self.assertEqual(self.cheap_variant.price, 149.0)
        self.assertEqual(self.expensive_variant.price, apply_markup(989900))
        self.assertEqual(self.expensive_variant.discount_price, apply_markup(950000))

    def test_inactive_variants_are_not_repriced(self):
        self.cheap_variant.is_active = False
        self.cheap_variant.save(update_fields=["is_active"])
        _run("--apply")
        self.cheap_variant.refresh_from_db()
        self.assertEqual(self.cheap_variant.price, 99)

    def test_running_apply_twice_changes_nothing(self):
        """The must-have idempotency test: run the backfill twice, the second
        run must not move the price again (no double markup)."""
        _run("--apply")
        self.cheap.refresh_from_db()
        self.expensive.refresh_from_db()
        after_first = (self.cheap.initial_selling_price, self.expensive.initial_selling_price,
                      self.expensive.discount_price)

        _run("--apply")
        self.cheap.refresh_from_db()
        self.expensive.refresh_from_db()
        after_second = (self.cheap.initial_selling_price, self.expensive.initial_selling_price,
                       self.expensive.discount_price)

        self.assertEqual(after_first, after_second)
        self.cheap_variant.refresh_from_db()
        self.assertEqual(self.cheap_variant.price, after_first[0])

    def test_second_dry_run_after_apply_reports_nothing_to_do(self):
        _run("--apply")
        output = _run()
        self.assertIn("Nothing to do", output)

    def test_a_product_that_already_has_base_price_is_left_alone(self):
        # Simulates a product already migrated by sync_source_prices or a
        # fresh import -- this command must never re-mark-up an already
        # marked-up price.
        self.cheap.base_price = 99
        self.cheap.initial_selling_price = 149  # already marked up
        self.cheap.save()
        _run("--apply")
        self.cheap.refresh_from_db()
        self.assertEqual(self.cheap.base_price, 99)
        self.assertEqual(self.cheap.initial_selling_price, 149)

    def test_a_product_with_bad_price_data_is_reported_not_silently_skipped(self):
        # initial_selling_price is a non-nullable FloatField, but a stray
        # negative value can still land in the DB via a raw update -- this
        # must be reported by name/reason, never silently dropped.
        Products.objects.filter(pk=self.cheap.pk).update(initial_selling_price=-10)
        output = _run()
        self.assertIn("Cheap Tee", output)
        self.assertIn("negative", output)
        self.assertIn("Skipped", output)

    def test_before_after_table_and_total_change_are_printed(self):
        output = _run()
        self.assertIn("Cheap Tee", output)
        self.assertIn("Gaming Laptop", output)
        self.assertIn("Total selling-price change", output)
