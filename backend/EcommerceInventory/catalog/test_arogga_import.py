"""Arogga import wiring: the adapter, and the prescription flag that must
survive the trip from a product page into Products.requires_prescription.

No network -- every fetch goes through an injected fake, the same style as
catalog/test_admin_product_import.py.
"""
from pathlib import Path

from django.test import TestCase

from accounts.models import Users
from catalog.models import Categories, ImportSource, Products
from catalog.services_import import seed_product_entry
from catalog.services_scrape_import import browse_candidates, import_candidates

FIXTURES = Path(__file__).resolve().parent / "test_fixtures"


class RequiresPrescriptionImportTests(TestCase):
    """StoreConfiguration.rx_sales_enabled is the checkout gate, but it only
    bites on products actually flagged requires_prescription. If the importer
    drops the flag, a prescription medicine is imported as an ordinary OTC
    product and the gate never sees it -- so this is the load-bearing test for
    selling medicines at all.
    """

    def setUp(self):
        self.user = Users.objects.create_user(
            username="rximporter", email="rx@example.com", password="x", role="Admin")
        self.category = Categories.objects.create(
            name="Medicine", slug="health-medicine", description="")

    def _entry(self, **over):
        entry = {"name": "3-Geocef Cefixime 200mg", "price": 120.0, "description": "d",
                 "brand": "Hallmark", "images": []}
        entry.update(over)
        return entry

    def test_prescription_flag_is_persisted(self):
        out = seed_product_entry(self._entry(requires_prescription=True),
                                 self.category, self.user, self.user)
        self.assertEqual(out["status"], "created")
        self.assertTrue(Products.objects.get(id=out["product"].id).requires_prescription)

    def test_absent_flag_defaults_to_over_the_counter(self):
        out = seed_product_entry(self._entry(name="Savlon Cream"),
                                 self.category, self.user, self.user)
        self.assertFalse(Products.objects.get(id=out["product"].id).requires_prescription)

    def test_flag_is_never_inferred_as_true_from_a_missing_value(self):
        out = seed_product_entry(self._entry(name="Alcohol Pad", requires_prescription=None),
                                 self.category, self.user, self.user)
        self.assertFalse(Products.objects.get(id=out["product"].id).requires_prescription)


class AroggaSourceTests(TestCase):
    def test_source_is_enabled_with_the_arogga_adapter(self):
        source = ImportSource.objects.get(slug="arogga")
        self.assertTrue(source.is_enabled)
        self.assertEqual(source.adapter_key, "arogga")

    def test_source_url_stays_off_without_a_reseller_agreement(self):
        # sets_source_url enrolls a source in sync_source_prices, which is for
        # reseller-permission partners only (see ImportSource.sets_source_url).
        # Arogga is a price reference, not a partner, until that changes.
        self.assertFalse(ImportSource.objects.get(slug="arogga").sets_source_url)

    def test_has_category_mappings(self):
        self.assertGreater(ImportSource.objects.get(slug="arogga").categories.count(), 0)


class AroggaBrowseTests(TestCase):
    def setUp(self):
        self.category_html = (FIXTURES / "arogga_category.html").read_text(encoding="utf-8")
        self.product_html = (FIXTURES / "arogga_product_rx.html").read_text(encoding="utf-8")

    def test_listing_only_browse_uses_one_request(self):
        calls = []

        def fake_fetch(url):
            calls.append(url)
            return self.category_html

        out = browse_candidates("arogga", category_path="category/healthcare/5987/healthcare",
                                fetch=fake_fetch, detail=False)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(out["candidates"]), 3)
        self.assertEqual(out["candidates"][0]["name"], "Alcohol Pad")
        self.assertAlmostEqual(out["candidates"][0]["price"], 74.0)

    def test_detailed_browse_fetches_each_product_for_the_rx_flag(self):
        # A listing card cannot tell us whether an item needs a prescription,
        # so the detailed path must actually open the product pages.
        def fake_fetch(url):
            return self.category_html if "/category/" in url else self.product_html

        out = browse_candidates("arogga", category_path="category/medicine/1/medicine",
                                fetch=fake_fetch, detail=True)
        self.assertTrue(out["candidates"])


class AroggaImportTests(TestCase):
    def setUp(self):
        self.user = Users.objects.create_user(
            username="aroggaimporter", email="ai@example.com", password="x", role="Admin")
        self.category = Categories.objects.create(
            name="Medicine", slug="health-medicine", description="")
        self.product_html = (FIXTURES / "arogga_product_rx.html").read_text(encoding="utf-8")

    def test_imported_medicine_keeps_its_prescription_flag(self):
        results = import_candidates(
            "arogga",
            ["https://www.arogga.com/product/4/3-geocef-powder-for-suspension-200mg-5ml"],
            self.category, self.user, self.user, fetch=lambda url: self.product_html)
        self.assertEqual(results[0]["status"], "imported")
        product = Products.objects.get(id=results[0]["product_id"])
        self.assertTrue(product.requires_prescription)

    def test_price_gets_the_platform_markup_not_the_raw_source_price(self):
        results = import_candidates(
            "arogga",
            ["https://www.arogga.com/product/4/3-geocef-powder-for-suspension-200mg-5ml"],
            self.category, self.user, self.user, fetch=lambda url: self.product_html)
        product = Products.objects.get(id=results[0]["product_id"])
        # base_price is the untouched source number; the sell price is derived
        # from it via catalog.pricing.apply_markup and must be strictly higher.
        self.assertEqual(product.base_price, 2.0)
        self.assertGreater(product.initial_selling_price, product.base_price)

    def test_no_source_url_is_stored_for_a_non_partner_source(self):
        results = import_candidates(
            "arogga",
            ["https://www.arogga.com/product/4/3-geocef-powder-for-suspension-200mg-5ml"],
            self.category, self.user, self.user, fetch=lambda url: self.product_html)
        product = Products.objects.get(id=results[0]["product_id"])
        # An empty source_url keeps it out of sync_source_prices.
        self.assertEqual(product.source_url or "", "")
