"""Arogga import wiring: the adapter, and the prescription flag that must
survive the trip from a product page into Products.requires_prescription.

No network -- every fetch goes through an injected fake, the same style as
catalog/test_admin_product_import.py.
"""
from pathlib import Path

from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from catalog.controllers.ProductImportController import AdminBrowseImportCandidatesView

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


class PrescriptionVisibleBeforeImportTests(TestCase):
    """The picker must say which candidates are prescription-only BEFORE the
    owner imports them.

    Without this the flag is invisible until after the fact: the products land
    silently blocked at checkout (rx_sales_enabled is off until a DGDA licence
    exists) and the only way to notice is to wonder why they never sell.
    """

    def setUp(self):
        self.category_html = (FIXTURES / "arogga_category.html").read_text(encoding="utf-8")
        self.rx_html = (FIXTURES / "arogga_product_rx.html").read_text(encoding="utf-8")

    def test_detailed_browse_reports_the_prescription_flag(self):
        def fake_fetch(url):
            return self.category_html if "/category/" in url else self.rx_html

        out = browse_candidates("arogga", category_path="category/medicine/6322/medicine",
                                fetch=fake_fetch, detail=True)
        self.assertTrue(out["candidates"])
        self.assertTrue(all(c["requires_prescription"] is True for c in out["candidates"]))

    def test_listing_only_browse_reports_unknown_not_false(self):
        # A listing card carries no prescription marker. Reporting False would
        # be a positive claim that the item is over-the-counter, which is the
        # dangerous direction to be wrong in -- so it stays None ("unknown")
        # and the UI can say so.
        out = browse_candidates("arogga", category_path="category/healthcare/5987/healthcare",
                                fetch=lambda url: self.category_html, detail=False)
        self.assertTrue(out["candidates"])
        self.assertTrue(all(c["requires_prescription"] is None for c in out["candidates"]))

    def test_non_medicine_sources_are_unaffected(self):
        # Every other adapter omits the key entirely; the candidate shape must
        # still carry it so one UI can render every source.
        from catalog.services_scrape_import import _candidate_from_product
        c = _candidate_from_product("https://x/y", {"name": "Laptop", "price": 100})
        self.assertIsNone(c["requires_prescription"])


class BrowseDetailParamTests(TestCase):
    """The browse view must honour ?detail=.

    The picker offers a "check prescription status" toggle, which is only
    meaningful if the API acts on it: detail=false is the one-request listing
    path, detail=true opens each product page. The view ignored the parameter
    entirely, so the fast path was unreachable and every browse paid the
    per-product fetch cost.
    """
    def setUp(self):
        self.factory = APIRequestFactory()
        self.owner = Users.objects.create_user(
            username="browseowner", email="bo@example.com", password="x",
            role="Super Admin", country="Bangladesh")

    def _browse(self, params):
        request = self.factory.get("/api/products/admin/import/browse/", params)
        force_authenticate(request, user=self.owner)
        with patch("catalog.controllers.ProductImportController.browse_candidates") as mocked:
            mocked.return_value = {"candidates": [], "categories": [],
                                   "listing_product_count": 0, "fetch_failures": 0}
            AdminBrowseImportCandidatesView.as_view()(request)
            return mocked.call_args

    def test_detail_false_is_passed_through(self):
        self.assertIs(self._browse({"source": "arogga", "category": "c", "detail": "false"}).kwargs["detail"], False)

    def test_detail_true_is_passed_through(self):
        self.assertIs(self._browse({"source": "arogga", "category": "c", "detail": "true"}).kwargs["detail"], True)

    def test_defaults_to_detailed_when_absent(self):
        # The safe default for a medicine source: a detailed browse is the only
        # one that can report prescription status at all.
        self.assertIs(self._browse({"source": "arogga", "category": "c"}).kwargs["detail"], True)

    def test_unrecognised_value_falls_back_to_detailed(self):
        self.assertIs(self._browse({"source": "arogga", "category": "c", "detail": "banana"}).kwargs["detail"], True)


class CandidateSellingPriceTests(TestCase):
    """The picker showed the SOURCE price, so the owner was choosing products
    without seeing what a customer would actually pay.

    The markup rule lives in catalog.pricing and must not be reimplemented in
    JavaScript — a drifting copy would quote a price the import then contradicts.
    So the candidate carries the computed selling price from the server.
    """

    def setUp(self):
        from core.models import StoreConfiguration
        from django.core.cache import cache
        cache.clear()
        cfg = StoreConfiguration.get_solo()
        cfg.markup_percentage = 3
        cfg.markup_floor = 50
        cfg.save()

    def test_candidate_carries_the_marked_up_selling_price(self):
        from catalog.services_scrape_import import _candidate_from_product
        c = _candidate_from_product("https://x/y", {"name": "Alcohol Pad", "price": 74.0})
        self.assertEqual(c["price"], 74.0)          # untouched source price
        self.assertEqual(c["selling_price"], 124.0)  # 74 + max(50, 3%)

    def test_percentage_wins_over_the_floor_on_an_expensive_item(self):
        from catalog.services_scrape_import import _candidate_from_product
        c = _candidate_from_product("https://x/y", {"name": "Laptop", "price": 100000.0})
        self.assertEqual(c["selling_price"], 103000.0)

    def test_discount_price_is_marked_up_too(self):
        from catalog.services_scrape_import import _candidate_from_product
        c = _candidate_from_product("https://x/y", {"name": "Tee", "price": 980.0, "discount_price": 850.0})
        self.assertEqual(c["selling_discount_price"], 900.0)

    def test_absent_price_yields_no_selling_price_rather_than_zero(self):
        from catalog.services_scrape_import import _candidate_from_product
        c = _candidate_from_product("https://x/y", {"name": "Mystery", "price": None})
        self.assertIsNone(c["selling_price"])

    def test_listing_cards_are_priced_the_same_way(self):
        from catalog.services_scrape_import import _candidate_from_card
        c = _candidate_from_card({"source_url": "https://x/y", "name": "Pad", "price": 74.0, "images": []})
        self.assertEqual(c["selling_price"], 124.0)
