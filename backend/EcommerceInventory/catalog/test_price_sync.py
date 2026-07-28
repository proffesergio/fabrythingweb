from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Users
from catalog.controllers.ProductController import AdminSyncPricesView
from catalog.models import Categories, Products
from catalog.services_price_sync import sync_source_prices

# NOTE ON FIXTURE DEVIATION: the task brief's own test snippet uses
# `span.price-new` / `span.price-old`, but the real parser
# (catalog.scrape_parsers.parse_opencart_product / _extract_prices) reads
# `div.price-wrapper` containing `span.special` (current price) and
# `span.price` (crossed-out original) -- verified against the real
# potakait.com markup captured in catalog/test_fixtures/opencart_product.html.
# Using the brief's simplified selectors here would make parse_opencart_product
# return price=None for both fields, so the numbers below (46,000 original /
# 44,500 current) are mirrored onto the *real* markup shape instead.
PAGE = """<html><head><base href="https://potakait.com/"></head><body>
<div class="product-overview-text-wrapper" id="product">
<div class="summary entry-summary">
<h1 class="product_title entry-title">Test GPU</h1>
<div class="price-wrapper">
<span class="special">44,500৳</span>
<span class="price">46,000৳</span>
</div>
</div>
</div>
</body></html>"""


def fake_fetcher(url):
    return PAGE

class PriceSyncTests(TestCase):
    def setUp(self):
        owner = Users.objects.create_user(username="r", email="r@x.com", password="x",
                                          role="Super Admin", country="Bangladesh")
        cat = Categories.objects.create(name="Components", slug="c-t", description="")
        self.p = Products.objects.create(
            name="Test GPU", slug="test-gpu", sku="FS-9001", category_id=cat,
            description="", initial_buying_price=1, initial_selling_price=40000,
            source_url="https://potakait.com/test-gpu",
            domain_user_id=owner, added_by_user_id=owner)

    def test_updates_price_and_stamps_sync(self):
        changes = sync_source_prices(fetcher=fake_fetcher)
        self.p.refresh_from_db()
        self.assertEqual(self.p.initial_selling_price, 46000.0)
        self.assertEqual(self.p.discount_price, 44500.0)
        self.assertEqual(self.p.source_price, 46000.0)
        self.assertIsNotNone(self.p.price_synced_at)
        self.assertEqual(len([c for c in changes if c["updated"]]), 1)

    def test_dry_run_writes_nothing(self):
        sync_source_prices(fetcher=fake_fetcher, dry_run=True)
        self.p.refresh_from_db()
        self.assertEqual(self.p.initial_selling_price, 40000)
        self.assertIsNone(self.p.price_synced_at)

    def test_markup_applied(self):
        sync_source_prices(fetcher=fake_fetcher, markup_percent=10)
        self.p.refresh_from_db()
        self.assertEqual(self.p.initial_selling_price, 50600.0)  # 46000 * 1.10

    def test_fetch_failure_skips_product(self):
        def boom(url):
            raise OSError("down")
        changes = sync_source_prices(fetcher=boom)
        self.p.refresh_from_db()
        self.assertEqual(self.p.initial_selling_price, 40000)
        self.assertFalse(changes[0]["updated"])

    def test_products_without_source_url_are_untouched(self):
        # Fabrilife / hand-entered products must never be re-priced by this.
        hand_entered = Products.objects.create(
            name="Hand Entered Shirt", slug="hand-entered-shirt", sku="FS-9002",
            category_id=self.p.category_id, description="",
            initial_buying_price=1, initial_selling_price=999,
            source_url="", domain_user_id=self.p.domain_user_id,
            added_by_user_id=self.p.domain_user_id)
        changes = sync_source_prices(fetcher=fake_fetcher)
        hand_entered.refresh_from_db()
        self.assertEqual(hand_entered.initial_selling_price, 999)
        self.assertIsNone(hand_entered.price_synced_at)
        self.assertNotIn("hand-entered-shirt", [c["slug"] for c in changes])


class AdminSyncPricesViewTests(TestCase):
    """Endpoint authorization tests, exercised directly against the view via
    APIRequestFactory + force_authenticate. Going through the full HTTP
    client would also route the request through
    core.middleware.PermissionMiddleware, which blocks any non-platform-scope
    user (400 "Module not Exist") before the view's own isPlatformScope check
    ever runs, since there is no ModuleUrls row for this endpoint (it isn't a
    sidebar page). That middleware behaviour is out of scope for this task --
    see accounts/test_dynamic_form_scope.py for the same pattern -- so the
    view's own authorization is tested at the view layer instead."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.owner = Users.objects.create_user(username="root", email="root@x.com",
                                                password="x", role="Super Admin",
                                                country="Bangladesh")
        self.staff = Users.objects.create_user(username="staff", email="staff@x.com",
                                                password="x", role="Staff",
                                                country="Bangladesh",
                                                domain_user_id=self.owner)

    @patch("catalog.controllers.ProductController.sync_source_prices")
    def test_platform_admin_can_sync(self, mock_sync):
        mock_sync.return_value = []
        request = self.factory.post("/api/products/admin/sync-prices/")
        force_authenticate(request, user=self.owner)
        response = AdminSyncPricesView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["checked"], 0)
        self.assertEqual(response.data["data"]["changes"], [])

    @patch("catalog.controllers.ProductController.sync_source_prices")
    def test_non_root_staff_forbidden(self, mock_sync):
        mock_sync.return_value = []
        request = self.factory.post("/api/products/admin/sync-prices/")
        force_authenticate(request, user=self.staff)
        response = AdminSyncPricesView.as_view()(request)
        self.assertEqual(response.status_code, 403)
        mock_sync.assert_not_called()
