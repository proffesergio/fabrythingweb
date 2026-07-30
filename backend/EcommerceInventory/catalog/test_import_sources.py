"""Tests for the DB-driven import control panel: ImportSource/
ImportSourceCategory/ImportRun models, the 0008 data migration that seeds
them from the previously-hardcoded dicts, the admin CRUD endpoints, and
ImportRun bookkeeping on the browse/import endpoints.

No test here hits the network -- every fetch goes through an injected fake,
same style as catalog/test_admin_product_import.py.
"""
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Users
from catalog.controllers.ImportSourceController import (
    AdminImportRunListView,
    AdminImportSourceCategoryDetailView,
    AdminImportSourceCategoryListCreateView,
    AdminImportSourceDetailView,
    AdminImportSourceListCreateView,
)
from catalog.controllers.ProductImportController import AdminImportProductsView
from catalog.models import Categories, ImportRun, ImportSource, ImportSourceCategory


def auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")


# --- Migration seed correctness ---------------------------------------------

class SeededImportSourcesTests(TestCase):
    """Pins the exact (source_path -> our_category_slug) mappings the 0008
    migration seeds -- these are the measured-working values from the owner's
    spec, verbatim. A regression here silently breaks re-imports for a whole
    category on a partner site."""

    def test_potakait_seeded_correctly(self):
        source = ImportSource.objects.get(slug="potakait")
        self.assertEqual(source.name, "Potakait.com")
        self.assertEqual(source.adapter_key, "opencart")
        self.assertFalse(source.supports_search)
        self.assertTrue(source.is_enabled)
        self.assertTrue(source.sets_source_url)

        mapping = dict(source.categories.values_list("source_path", "our_category_slug"))
        self.assertEqual(mapping, {
            "laptops": "computers-laptops",
            "gaming-pc": "computers-desktops",
            "monitors": "computers-monitors",
            "processors": "computers-components",
            "keyboards": "computers-keyboards-mice",
            "printers": "computers-printers-office",
            "router": "computers-networking",
            "earbuds": "gadgets-earbuds",
            "headphones": "gadgets-earbuds",
            "speaker-and-home-theater": "gadgets-speakers",
            "power-bank": "gadgets-power",
            "smart-watches": "gadgets-smart-watches",
            "action-camera": "gadgets-cameras",
            "mobile-phone-accessories": "gadgets-cases",
            "tablet-pc": "phones-tablets",
            "gadgets": "gadgets",
        })

    def test_canvasit_seeded_correctly(self):
        source = ImportSource.objects.get(slug="canvasit")
        self.assertEqual(source.adapter_key, "opencart")
        self.assertTrue(source.supports_search)
        self.assertTrue(source.is_enabled)
        self.assertTrue(source.sets_source_url)

        mapping = dict(source.categories.values_list("source_path", "our_category_slug"))
        self.assertEqual(mapping, {
            "laptop": "computers-laptops",
            "desktop-pc": "computers-desktops",
            "monitor": "computers-monitors",
            "processor": "computers-components",
            "keyboard": "computers-keyboards-mice",
            "printer": "computers-printers-office",
            "router": "computers-networking",
            "earbuds": "gadgets-earbuds",
            "headphone": "gadgets-earbuds",
            "speaker": "gadgets-speakers",
            "power-bank": "gadgets-power",
            "smart-watch": "gadgets-smart-watches",
            "action-camera": "gadgets-cameras",
            "drones": "gadgets-cameras",
            "mobile-phone-accessories": "gadgets-cases",
            "phone-tablet": "phones-tablets",
            "gadget": "gadgets",
        })

    def test_fabrilife_seeded_with_source_url_false(self):
        source = ImportSource.objects.get(slug="fabrilife")
        self.assertEqual(source.adapter_key, "fabrilife")
        self.assertTrue(source.supports_search)
        self.assertTrue(source.is_enabled)
        # Load-bearing distinction: Fabrilife is NOT a reseller partner, so
        # imports from it must never enrol a product into the price-sync job.
        self.assertFalse(source.sets_source_url)
        self.assertEqual(source.categories.count(), 8)

    def test_arogga_seeded_disabled_with_reason(self):
        source = ImportSource.objects.get(slug="arogga")
        self.assertFalse(source.is_enabled)
        self.assertEqual(source.adapter_key, "")
        self.assertFalse(source.sets_source_url)
        self.assertIn("client-rendered", source.notes)
        self.assertEqual(source.categories.count(), 0)


# --- Authorization -----------------------------------------------------------

class ImportSourceAuthorizationTests(TestCase):
    """A Customer (self-signed-up, its own domain root -- same trap
    core.helpers.isPlatformStaff exists for) must get 403 on every one of
    these admin endpoints, not just the browse/import pair."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.owner = Users.objects.create_user(
            username="root2", email="root2@x.com", password="x",
            role="Super Admin", country="Bangladesh")
        self.customer = Users.objects.create_user(
            username="cust2", email="cust2@x.com", password="x",
            role="Customer", country="Bangladesh")
        self.potakait = ImportSource.objects.get(slug="potakait")
        self.mapping = self.potakait.categories.first()

    def test_customer_forbidden_on_source_list_create(self):
        request = self.factory.get("/api/products/admin/import/sources/")
        force_authenticate(request, user=self.customer)
        res = AdminImportSourceListCreateView.as_view()(request)
        self.assertEqual(res.status_code, 403)

        request = self.factory.post("/api/products/admin/import/sources/", {}, format="json")
        force_authenticate(request, user=self.customer)
        res = AdminImportSourceListCreateView.as_view()(request)
        self.assertEqual(res.status_code, 403)

    def test_customer_forbidden_on_source_detail(self):
        request = self.factory.patch(
            f"/api/products/admin/import/sources/{self.potakait.id}/",
            {"is_enabled": False}, format="json")
        force_authenticate(request, user=self.customer)
        res = AdminImportSourceDetailView.as_view()(request, pk=self.potakait.id)
        self.assertEqual(res.status_code, 403)

    def test_customer_forbidden_on_source_categories(self):
        request = self.factory.get(f"/api/products/admin/import/sources/{self.potakait.id}/categories/")
        force_authenticate(request, user=self.customer)
        res = AdminImportSourceCategoryListCreateView.as_view()(request, source_pk=self.potakait.id)
        self.assertEqual(res.status_code, 403)

    def test_customer_forbidden_on_source_category_detail(self):
        request = self.factory.patch(
            f"/api/products/admin/import/source-categories/{self.mapping.id}/",
            {"label": "x"}, format="json")
        force_authenticate(request, user=self.customer)
        res = AdminImportSourceCategoryDetailView.as_view()(request, pk=self.mapping.id)
        self.assertEqual(res.status_code, 403)

    def test_customer_forbidden_on_run_list(self):
        # Goes through APIClient (not APIRequestFactory) because ImportRun's
        # PermissionDenied path is only raised inside get_queryset(), which
        # only runs once DRF's own dispatch/exception-handling machinery is
        # live -- APIRequestFactory + a bare as_view() call skips that.
        client = APIClient()
        auth(client, self.customer)
        res = client.get("/api/products/admin/import/runs/")
        self.assertEqual(res.status_code, 403)

    def test_owner_allowed_on_every_endpoint(self):
        request = self.factory.get("/api/products/admin/import/sources/")
        force_authenticate(request, user=self.owner)
        res = AdminImportSourceListCreateView.as_view()(request)
        self.assertEqual(res.status_code, 200)

        client = APIClient()
        auth(client, self.owner)
        res = client.get("/api/products/admin/import/runs/")
        self.assertEqual(res.status_code, 200)


# --- Enable/disable validation -----------------------------------------------

class ImportSourceManagementTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.owner = Users.objects.create_user(
            username="root3", email="root3@x.com", password="x",
            role="Super Admin", country="Bangladesh")

    def test_cannot_enable_source_with_no_adapter(self):
        request = self.factory.patch(
            "/api/products/admin/import/sources/", {"is_enabled": True}, format="json")
        force_authenticate(request, user=self.owner)
        arogga = ImportSource.objects.get(slug="arogga")
        res = AdminImportSourceDetailView.as_view()(request, pk=arogga.id)
        self.assertEqual(res.status_code, 400)
        arogga.refresh_from_db()
        self.assertFalse(arogga.is_enabled)

    def test_can_add_a_new_source_and_its_category_mapping(self):
        request = self.factory.post("/api/products/admin/import/sources/", {
            "name": "New Store", "slug": "newstore", "base_url": "https://newstore.example/",
            "adapter_key": "opencart", "supports_search": True, "is_enabled": True,
            "sets_source_url": True,
        }, format="json")
        force_authenticate(request, user=self.owner)
        res = AdminImportSourceListCreateView.as_view()(request)
        self.assertEqual(res.status_code, 201, res.data)
        source_id = res.data["data"]["id"]

        request = self.factory.post(
            f"/api/products/admin/import/sources/{source_id}/categories/",
            {"source_path": "phones", "label": "Phones", "our_category_slug": "phones-smartphones"},
            format="json")
        force_authenticate(request, user=self.owner)
        res = AdminImportSourceCategoryListCreateView.as_view()(request, source_pk=source_id)
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(ImportSourceCategory.objects.filter(source_id=source_id).count(), 1)

    def test_disabling_a_source_is_rejected_by_import_api(self):
        # Flip potakait off, then confirm the import endpoint (not just the
        # management endpoint) refuses it with a clear message rather than
        # quietly returning zero results.
        potakait = ImportSource.objects.get(slug="potakait")
        potakait.is_enabled = False
        potakait.save(update_fields=["is_enabled"])

        cat = Categories.objects.create(name="Cat", slug="import-cat-x", description="")
        request = self.factory.post("/api/products/admin/import/", {
            "source": "potakait", "source_urls": ["https://potakait.com/x"], "category_id": cat.id,
        }, format="json")
        force_authenticate(request, user=self.owner)
        res = AdminImportProductsView.as_view()(request)
        self.assertEqual(res.status_code, 400)
        self.assertIn("source", res.data["field_errors"])
        self.assertEqual(ImportRun.objects.filter(source=potakait).count(), 0)


# --- ImportRun bookkeeping ----------------------------------------------------

def _opencart_product_page(name, price):
    return f"""<html><head><base href="https://potakait.com/"></head><body>
<h1 class="product_title">{name}</h1>
<div class="price-wrapper"><span class="special">{price}৳</span></div>
<div id="gallery"><img src="gallery/img1.jpg"></div>
</body></html>"""


class ImportRunBookkeepingTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.owner = Users.objects.create_user(
            username="root4", email="root4@x.com", password="x",
            role="Super Admin", country="Bangladesh")
        self.cat = Categories.objects.create(name="Run Cat", slug="run-cat", description="")

    def do_import(self, urls):
        request = self.factory.post("/api/products/admin/import/", {
            "source": "potakait", "source_urls": urls, "category_id": self.cat.id,
        }, format="json")
        force_authenticate(request, user=self.owner)
        return AdminImportProductsView.as_view()(request)

    def test_import_run_records_counts_on_success(self):
        def fake_fetch(url):
            return _opencart_product_page("Run Phone", 10000)

        with patch("catalog.services_scrape_import.polite_get", side_effect=fake_fetch), \
             patch("catalog.services_import.import_image", return_value="https://cdn.test/x.jpg"):
            res = self.do_import(["https://potakait.com/run-phone"])

        self.assertEqual(res.status_code, 200, res.data)
        run_id = res.data["data"]["run_id"]
        run = ImportRun.objects.get(pk=run_id)
        self.assertEqual(run.status, ImportRun.STATUS_COMPLETED)
        self.assertEqual(run.found_count, 1)
        self.assertEqual(run.imported_count, 1)
        self.assertEqual(run.skipped_count, 0)
        self.assertEqual(run.failed_count, 0)
        self.assertIsNotNone(run.finished_at)
        self.assertEqual(run.triggered_by_user_id, self.owner)

        self.potakait_last_synced_updates()

    def potakait_last_synced_updates(self):
        source = ImportSource.objects.get(slug="potakait")
        self.assertIsNotNone(source.last_synced_at)

    def test_import_run_records_skipped_and_failed(self):
        def fake_fetch(url):
            if "no-price" in url:
                return """<html><head><base href="https://potakait.com/"></head><body>
                <h1 class="product_title">No Price</h1></body></html>"""
            return _opencart_product_page("Existing Phone", 5000)

        from catalog.models import Products
        Products.objects.create(
            name="Existing Phone", slug="existing-phone", sku="RUN-0001", category_id=self.cat,
            description="", initial_buying_price=1, initial_selling_price=100,
            domain_user_id=self.owner, added_by_user_id=self.owner)

        with patch("catalog.services_scrape_import.polite_get", side_effect=fake_fetch):
            res = self.do_import([
                "https://potakait.com/existing-phone",
                "https://potakait.com/no-price",
            ])

        self.assertEqual(res.status_code, 200, res.data)
        run = ImportRun.objects.get(pk=res.data["data"]["run_id"])
        self.assertEqual(run.found_count, 2)
        self.assertEqual(run.imported_count, 0)
        self.assertEqual(run.skipped_count, 1)
        self.assertEqual(run.failed_count, 1)
        self.assertEqual(run.status, ImportRun.STATUS_COMPLETED)

    def test_import_run_marked_failed_on_whole_batch_blowup(self):
        with patch("catalog.controllers.ProductImportController.import_candidates",
                   side_effect=RuntimeError("category vanished mid-request")):
            res = self.do_import(["https://potakait.com/x"])

        self.assertEqual(res.status_code, 500)
        run = ImportRun.objects.get(source__slug="potakait")
        self.assertEqual(run.status, ImportRun.STATUS_FAILED)
        self.assertIn("category vanished", run.error_summary)
        self.assertIsNotNone(run.finished_at)

    def test_run_list_filters_by_source(self):
        def fake_fetch(url):
            return _opencart_product_page("List Phone", 8000)

        with patch("catalog.services_scrape_import.polite_get", side_effect=fake_fetch), \
             patch("catalog.services_import.import_image", return_value="https://cdn.test/x.jpg"):
            self.do_import(["https://potakait.com/list-phone"])

        client = APIClient()
        auth(client, self.owner)
        res = client.get("/api/products/admin/import/runs/", {"source": "potakait"})
        self.assertEqual(res.status_code, 200)
        rows = res.data["data"]["data"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_slug"], "potakait")

        res = client.get("/api/products/admin/import/runs/", {"source": "fabrilife"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data["data"]["data"]), 0)
