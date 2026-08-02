"""Admin product-import tool: browse candidates from potakait.com,
canvasit.com.bd and fabrilife.com, then import a picked subset into our
catalog.

Exercised directly against the views via APIRequestFactory + force_authenticate
(see catalog/test_price_sync.py::AdminSyncPricesViewTests / test_admin_quick_
update.py for why: going through the full HTTP client would route the
request through core.middleware.PermissionMiddleware, which blocks any
non-platform-scope user before the view's own isPlatformScope check ever
runs, since there is no ModuleUrls row for this brand-new endpoint).

No test here hits the network: every fetch goes through an injected fake, in
the same style as catalog/test_price_sync.py's `fake_fetcher`.
"""
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Users
from catalog.controllers.ProductImportController import (
    AdminBrowseImportCandidatesView,
    AdminImportProductsView,
)
from catalog.models import Categories, Products
from catalog.services_scrape_import import IMPORT_LIMIT

# --- Fake pages -------------------------------------------------------------

OPENCART_LISTING = """<html><body>
<div class="product-item"><a href="https://potakait.com/phone-a">Phone A</a></div>
<div class="product-item"><a href="https://potakait.com/phone-b">Phone B</a></div>
</body></html>"""

def _opencart_product_page(name, price, discount=None, images=None):
    images = images or ["gallery/img1.jpg"]
    img_tags = "".join(f'<img src="{u}">' for u in images)
    # potakait markup: span.special is always the current/lower price; when
    # discounted, span.price additionally holds the crossed-out original --
    # see catalog/scrape_parsers.py's _extract_prices_potakait.
    disc_html = f'<span class="price">{price}৳</span>' if discount else ""
    special = discount if discount else price
    return f"""<html><head><base href="https://potakait.com/"></head><body>
<h1 class="product_title">{name}</h1>
<div class="price-wrapper"><span class="special">{special}৳</span>{disc_html}</div>
<div id="gallery">{img_tags}</div>
</body></html>"""


FABRILIFE_LISTING_JSON = """{"hits": [
  {"id": 1, "slug": "fab-tee-one"},
  {"id": 2, "slug": "fab-tee-two"}
]}"""


def _fabrilife_product_page(name, price):
    return f"""<html><head><meta property="og:url" content="https://fabrilife.com/product/1-fab-tee-one"></head>
<body>
<div class="product-title-row"><h4 class="tiny-margin">{name}</h4></div>
<div class="price-now"><span class="price_field">{price}৳</span></div>
</body></html>"""


class AdminProductImportTestBase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.owner = Users.objects.create_user(
            username="root", email="root@x.com", password="x",
            role="Super Admin", country="Bangladesh")
        self.staff = Users.objects.create_user(
            username="staff", email="staff@x.com", password="x",
            role="Staff", country="Bangladesh", domain_user_id=self.owner)
        self.cat = Categories.objects.create(name="Smartphones", slug="phones-smartphones", description="")

    def browse(self, params, user):
        request = self.factory.get("/api/products/admin/import/browse/", params)
        force_authenticate(request, user=user)
        return AdminBrowseImportCandidatesView.as_view()(request)

    def do_import(self, data, user):
        request = self.factory.post(
            "/api/products/admin/import/", data, format="json")
        force_authenticate(request, user=user)
        return AdminImportProductsView.as_view()(request)


class BrowseCandidatesTests(AdminProductImportTestBase):
    def test_non_platform_user_forbidden(self):
        res = self.browse({"source": "potakait", "category": "smart-phone"}, self.staff)
        self.assertEqual(res.status_code, 403)

    def test_unknown_source_rejected(self):
        res = self.browse({"source": "arogga", "category": "x"}, self.owner)
        self.assertEqual(res.status_code, 400)

    def test_missing_category_and_query_rejected(self):
        res = self.browse({"source": "potakait"}, self.owner)
        self.assertEqual(res.status_code, 400)

    def test_browse_returns_candidates_with_already_have_flag(self):
        # "Phone A" already exists in our catalog (by slug) -- must be flagged.
        # (Named "Phone A/B" for continuity with the rest of this file, but the
        # category itself is "laptops" -- one of the verified potakait paths.)
        Products.objects.create(
            name="Phone A", slug="phone-a", sku="FS-9500", category_id=self.cat,
            description="", initial_buying_price=1, initial_selling_price=100,
            domain_user_id=self.owner, added_by_user_id=self.owner)

        def fake_fetch(url):
            if url.endswith("laptops"):
                return OPENCART_LISTING
            if "phone-a" in url:
                return _opencart_product_page("Phone A", 25000)
            return _opencart_product_page("Phone B", 30000, discount=28000)

        with patch("catalog.services_scrape_import.polite_get", side_effect=fake_fetch):
            res = self.browse({"source": "potakait", "category": "laptops"}, self.owner)

        self.assertEqual(res.status_code, 200, res.data)
        data = res.data["data"]
        candidates = data["candidates"]
        self.assertEqual(len(candidates), 2)
        by_name = {c["name"]: c for c in candidates}
        self.assertTrue(by_name["Phone A"]["already_have"])
        self.assertFalse(by_name["Phone B"]["already_have"])
        self.assertEqual(by_name["Phone B"]["price"], 30000)
        self.assertEqual(by_name["Phone B"]["discount_price"], 28000)
        self.assertTrue(by_name["Phone B"]["source_url"].startswith("https://potakait.com/"))
        self.assertTrue(by_name["Phone B"]["images"])
        # The verified category list comes back so the UI can offer a dropdown.
        self.assertTrue(any(c["path"] == "laptops" for c in data["categories"]))
        # Zero-vs-unreachable bookkeeping: both product links were found and
        # both fetched cleanly.
        self.assertEqual(data["listing_product_count"], 2)
        self.assertEqual(data["fetch_failures"], 0)

    def test_browse_potakait_search_rejected(self):
        # potakait.com has no working search endpoint (verified live: every
        # plausible URL 404s) -- a search request must be refused with a
        # field-attributed error, never silently return zero results.
        res = self.browse({"source": "potakait", "q": "phone"}, self.owner)
        self.assertEqual(res.status_code, 400)
        self.assertIn("q", res.data["field_errors"])

    def test_browse_canvasit_search_works(self):
        def fake_fetch(url):
            if "route=product/search" in url:
                return OPENCART_LISTING
            return _opencart_product_page("Canvasit Phone", 20000)

        with patch("catalog.services_scrape_import.polite_get", side_effect=fake_fetch):
            res = self.browse({"source": "canvasit", "q": "phone"}, self.owner)

        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(len(res.data["data"]["candidates"]), 2)

    def test_browse_reports_fetch_failures_distinct_from_empty(self):
        # The listing itself resolves and lists 2 product URLs, but every
        # per-product fetch then fails -- this must NOT look identical to "0
        # products in this category" in the response.
        def fake_fetch(url):
            if url.endswith("laptops"):
                return OPENCART_LISTING
            raise TimeoutError("no route to host")

        with patch("catalog.services_scrape_import.polite_get", side_effect=fake_fetch):
            res = self.browse({"source": "potakait", "category": "laptops"}, self.owner)

        self.assertEqual(res.status_code, 200, res.data)
        data = res.data["data"]
        self.assertEqual(data["candidates"], [])
        self.assertEqual(data["listing_product_count"], 2)
        self.assertEqual(data["fetch_failures"], 2)

    def test_gadget_and_tablet_categories_verified_for_both_opencart_sources(self):
        # Neither site sells smartphones (only tablets + accessories), but
        # both DO carry earbuds/headphones/speakers/power banks/smart
        # watches/action cameras/phone accessories/tablets -- verified live
        # 2026-07-29. These must be offered in the category dropdown, mapped
        # to our taxonomy, distinct from the computer-hardware categories.
        def fake_fetch(url):
            return OPENCART_LISTING

        with patch("catalog.services_scrape_import.polite_get", side_effect=fake_fetch):
            potakait = self.browse({"source": "potakait", "category": "earbuds"}, self.owner)
            canvasit = self.browse({"source": "canvasit", "category": "phone-tablet"}, self.owner)

        self.assertEqual(potakait.status_code, 200, potakait.data)
        self.assertEqual(canvasit.status_code, 200, canvasit.data)

        potakait_paths = {c["path"]: c["our_category"] for c in potakait.data["data"]["categories"]}
        canvasit_paths = {c["path"]: c["our_category"] for c in canvasit.data["data"]["categories"]}

        self.assertEqual(potakait_paths["earbuds"], "gadgets-earbuds")
        self.assertEqual(potakait_paths["headphones"], "gadgets-earbuds")
        self.assertEqual(potakait_paths["tablet-pc"], "phones-tablets")
        self.assertEqual(potakait_paths["gadgets"], "gadgets")
        self.assertNotIn("phones-smartphones", potakait_paths.values())

        self.assertEqual(canvasit_paths["phone-tablet"], "phones-tablets")
        self.assertEqual(canvasit_paths["drones"], "gadgets-cameras")
        self.assertEqual(canvasit_paths["gadget"], "gadgets")
        self.assertNotIn("phones-smartphones", canvasit_paths.values())

    def test_browse_fabrilife_listing(self):
        def fake_fetch(url):
            return _fabrilife_product_page("Fab Tee", 990)

        with patch("catalog.services_scrape_import._fabrilife_search", return_value=FABRILIFE_LISTING_JSON), \
             patch("catalog.services_scrape_import.polite_get", side_effect=fake_fetch):
            res = self.browse({"source": "fabrilife", "category": "men-tshirts"}, self.owner)

        self.assertEqual(res.status_code, 200, res.data)
        candidates = res.data["data"]["candidates"]
        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0]["price"], 990)

    def test_browse_rokomari_via_catalog_importer_still_fetches_full_per_product_detail(self):
        # Regression guard: the affiliate picker's listing-only browse
        # (detail=False) must NOT change the catalog import tool's own browse
        # path -- ProductImportController never passes `detail`, so it must
        # keep getting the original one-fetch-per-candidate behaviour (needed
        # because the picker here decides what to actually import).
        roko_listing = """<html><body>
        <div class="product-card-wrapper"><a href="/product/1/item-a">Item A</a></div>
        <div class="product-card-wrapper"><a href="/product/2/item-b">Item B</a></div>
        </body></html>"""

        def _roko_product_page(name, price):
            return f"""<html><body>
            <h1 class="title">{name}</h1>
            <div class="details-stationary__price"><span class="sell-price">TK.{price}</span></div>
            </body></html>"""

        calls = []

        def fake_fetch(url):
            calls.append(url)
            if url.endswith("beauty-health"):
                return roko_listing
            if "item-a" in url:
                return _roko_product_page("Item A", 100)
            return _roko_product_page("Item B", 200)

        with patch("catalog.services_scrape_import.polite_get", side_effect=fake_fetch):
            res = self.browse({"source": "rokomari", "category": "product/category/2355/beauty-health"}, self.owner)

        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(len(res.data["data"]["candidates"]), 2)
        # 1 listing fetch + 1 fetch per candidate -- the full per-product loop,
        # not the affiliate picker's single-fetch shortcut.
        self.assertEqual(len(calls), 3)


class ImportProductsTests(AdminProductImportTestBase):
    def test_non_platform_user_forbidden(self):
        res = self.do_import(
            {"source": "potakait", "source_urls": ["https://potakait.com/phone-a"],
             "category_id": self.cat.id}, self.staff)
        self.assertEqual(res.status_code, 403)

    def test_batch_capped(self):
        urls = [f"https://potakait.com/p{i}" for i in range(IMPORT_LIMIT + 1)]
        res = self.do_import(
            {"source": "potakait", "source_urls": urls, "category_id": self.cat.id}, self.owner)
        self.assertEqual(res.status_code, 400)

    def test_import_creates_product_variant_and_images_potakait_sets_source_url(self):
        def fake_fetch(url):
            return _opencart_product_page("New Phone", 15000)

        with patch("catalog.services_scrape_import.polite_get", side_effect=fake_fetch), \
             patch("catalog.services_import.import_image", return_value="https://cdn.test/x.jpg"):
            res = self.do_import(
                {"source": "potakait", "source_urls": ["https://potakait.com/new-phone"],
                 "category_id": self.cat.id}, self.owner)

        self.assertEqual(res.status_code, 200, res.data)
        results = res.data["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "imported")

        product = Products.objects.get(slug="new-phone")
        # Import goes through catalog.services_import.seed_product_entry,
        # which stores the scraped price as base_price and derives the
        # selling price via apply_markup (defaults floor=50/3%): 3% of
        # 15000 is 450, above the floor.
        self.assertEqual(product.base_price, 15000)
        self.assertEqual(product.initial_selling_price, 15450.0)
        self.assertEqual(product.source_url, "https://potakait.com/new-phone")
        self.assertTrue(product.image)
        self.assertTrue(product.variants.filter(is_active=True).exists())

    def test_fabrilife_import_leaves_source_url_blank(self):
        def fake_fetch(url):
            return _fabrilife_product_page("Fab Import Tee", 1200)

        with patch("catalog.services_scrape_import.polite_get", side_effect=fake_fetch), \
             patch("catalog.services_import.import_image", return_value="https://cdn.test/x.jpg"):
            res = self.do_import(
                {"source": "fabrilife", "source_urls": ["https://fabrilife.com/product/1-fab-import-tee"],
                 "category_id": self.cat.id}, self.owner)

        self.assertEqual(res.status_code, 200, res.data)
        product = Products.objects.get(slug="fab-import-tee")
        self.assertEqual(product.source_url, "")

    def test_priceless_product_skipped_with_reason(self):
        def fake_fetch(url):
            return """<html><head><base href="https://potakait.com/"></head><body>
            <h1 class="product_title">No Price Phone</h1>
            </body></html>"""

        with patch("catalog.services_scrape_import.polite_get", side_effect=fake_fetch):
            res = self.do_import(
                {"source": "potakait", "source_urls": ["https://potakait.com/no-price"],
                 "category_id": self.cat.id}, self.owner)

        self.assertEqual(res.status_code, 200, res.data)
        result = res.data["data"]["results"][0]
        self.assertEqual(result["status"], "failed")
        self.assertIn("price", result["reason"].lower())
        self.assertFalse(Products.objects.filter(slug="no-price-phone").exists())

    def test_reimport_skips_already_existing(self):
        def fake_fetch(url):
            return _opencart_product_page("Repeat Phone", 12000)

        with patch("catalog.services_scrape_import.polite_get", side_effect=fake_fetch), \
             patch("catalog.services_import.import_image", return_value="https://cdn.test/x.jpg"):
            self.do_import(
                {"source": "potakait", "source_urls": ["https://potakait.com/repeat-phone"],
                 "category_id": self.cat.id}, self.owner)
            self.assertEqual(Products.objects.filter(slug="repeat-phone").count(), 1)

            res = self.do_import(
                {"source": "potakait", "source_urls": ["https://potakait.com/repeat-phone"],
                 "category_id": self.cat.id}, self.owner)

        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["data"]["results"][0]["status"], "skipped_exists")
        self.assertEqual(Products.objects.filter(slug="repeat-phone").count(), 1)

    def test_unknown_category_rejected(self):
        res = self.do_import(
            {"source": "potakait", "source_urls": ["https://potakait.com/x"],
             "category_id": 999999}, self.owner)
        self.assertEqual(res.status_code, 400)

    def test_fetch_failure_recorded_as_failed_not_raised(self):
        def fake_fetch(url):
            raise TimeoutError("no route to host")

        with patch("catalog.services_scrape_import.polite_get", side_effect=fake_fetch):
            res = self.do_import(
                {"source": "potakait", "source_urls": ["https://potakait.com/dead"],
                 "category_id": self.cat.id}, self.owner)

        self.assertEqual(res.status_code, 200, res.data)
        result = res.data["data"]["results"][0]
        self.assertEqual(result["status"], "failed")
