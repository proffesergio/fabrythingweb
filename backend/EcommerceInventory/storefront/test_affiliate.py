"""Rokomari affiliate automation: link construction, the click-through
redirect, scheduling/placement filters on the public list, and admin
authorization -- see storefront/services_affiliate.py and
storefront/views_affiliate.py.

No test here hits the network: the search endpoint patches
catalog.services_scrape_import.polite_get exactly like catalog/
test_import_sources.py does for the existing rokomari import flow.
"""
from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Users
from catalog.models import Categories
from storefront.models import AffiliateConfig, AffiliateProduct
from storefront.services_affiliate import build_affiliate_link, extract_rokomari_product_id


def auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(user).access_token)}")


def make_affiliate_product(**kwargs):
    defaults = dict(
        program="rokomari", remote_product_id="531074",
        source_url="https://www.rokomari.com/product/531074/some-item",
        title="Some Item", brand="TestBrand",
        original_price="590.00", current_price="554.00",
        is_active=True,
    )
    defaults.update(kwargs)
    return AffiliateProduct.objects.create(**defaults)


# --- Link construction --------------------------------------------------


class AffiliateLinkConstructionTests(TestCase):
    """The constructed link must always carry the admin-editable config's
    affId/affs/cma -- never a hardcoded value -- plus the right productId
    (cart link) or the product path (product-page link)."""

    def setUp(self):
        # AffiliateConfig.get_solo() caches the singleton (same pattern as
        # core.models.StoreConfiguration) -- the cache is a process-wide
        # LocMemCache that Django's per-test transaction rollback does NOT
        # clear, so a config mutation in one test would otherwise leak into
        # the next. Clear it so each test starts from get_solo()'s
        # create-with-defaults path, matching a fresh deploy.
        cache.clear()

    def test_cart_link_contains_configured_params_and_product_id(self):
        product = make_affiliate_product(link_type="CART", remote_product_id="531074")
        url = build_affiliate_link(product)
        self.assertTrue(url.startswith("https://www.rokomari.com/quick-cart?"))
        self.assertIn("affId=Ma8A710222i0iRo", url)
        self.assertIn("affs=70278", url)
        self.assertIn("cma=604800", url)
        self.assertIn("productId=531074", url)

    def test_product_link_contains_configured_params_and_product_path(self):
        product = make_affiliate_product(
            link_type="PRODUCT", remote_product_id="210626", title="Ashol Extra Virgin Olive Oil")
        url = build_affiliate_link(product)
        self.assertTrue(url.startswith("https://www.rokomari.com/product/210626/"))
        self.assertIn("affId=Ma8A710222i0iRo", url)
        self.assertIn("affs=70278", url)
        self.assertIn("cma=604800", url)
        # Product-page form has no productId param -- the id is in the path.
        self.assertNotIn("productId=", url)

    def test_config_change_is_reflected_without_touching_products(self):
        product = make_affiliate_product(link_type="CART")
        config = AffiliateConfig.get_solo()
        config.affiliate_id = "NEWID123"
        config.sub_id = "99999"
        config.save()
        url = build_affiliate_link(product)
        self.assertIn("affId=NEWID123", url)
        self.assertIn("affs=99999", url)

    def test_manual_short_link_overrides_constructed_url(self):
        product = make_affiliate_product(
            link_type="CART", manual_short_link="https://rkmri.co/R5MEpp0p0IEI/")
        url = build_affiliate_link(product)
        self.assertEqual(url, "https://rkmri.co/R5MEpp0p0IEI/")

    def test_extract_rokomari_product_id_from_product_url(self):
        self.assertEqual(
            extract_rokomari_product_id(
                "https://www.rokomari.com/product/210626/ashol-extra-virgin-olive-oil"),
            "210626",
        )

    def test_extract_rokomari_product_id_ignores_category_urls(self):
        self.assertIsNone(
            extract_rokomari_product_id("https://www.rokomari.com/product/category/2355/beauty-health"))

    def test_extract_rokomari_product_id_none_for_unrelated_url(self):
        self.assertIsNone(extract_rokomari_product_id("https://example.com/nothing-here"))


# --- Click-through redirect ----------------------------------------------


class AffiliateClickRedirectTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_click_increments_count_and_redirects_to_constructed_link(self):
        product = make_affiliate_product(link_type="CART", remote_product_id="531074")
        res = self.client.get(f"/api/store/affiliate/{product.id}/go/")
        self.assertEqual(res.status_code, 302)
        self.assertIn("affId=Ma8A710222i0iRo", res.url)
        self.assertIn("productId=531074", res.url)
        product.refresh_from_db()
        self.assertEqual(product.click_count, 1)

    def test_click_redirects_to_manual_override_when_set(self):
        product = make_affiliate_product(manual_short_link="https://rkmri.co/abc123/")
        res = self.client.get(f"/api/store/affiliate/{product.id}/go/")
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, "https://rkmri.co/abc123/")

    def test_click_count_increments_are_not_lost_across_concurrent_style_calls(self):
        """Regression guard for the atomic-F()-update requirement: firing the
        same click twice in a row (simulating two nearly-simultaneous
        requests, since Django's test client is single-threaded) must land
        both increments -- a read-modify-write bug reading a stale in-memory
        object would still pass a single-call test but silently drop one of
        two concurrent hits."""
        product = make_affiliate_product()
        self.client.get(f"/api/store/affiliate/{product.id}/go/")
        self.client.get(f"/api/store/affiliate/{product.id}/go/")
        product.refresh_from_db()
        self.assertEqual(product.click_count, 2)

    def test_inactive_product_404s(self):
        product = make_affiliate_product(is_active=False)
        res = self.client.get(f"/api/store/affiliate/{product.id}/go/")
        self.assertEqual(res.status_code, 404)

    def test_expired_product_404s(self):
        product = make_affiliate_product(ends_at=timezone.now() - timedelta(days=1))
        res = self.client.get(f"/api/store/affiliate/{product.id}/go/")
        self.assertEqual(res.status_code, 404)

    def test_not_yet_started_product_404s(self):
        product = make_affiliate_product(starts_at=timezone.now() + timedelta(days=1))
        res = self.client.get(f"/api/store/affiliate/{product.id}/go/")
        self.assertEqual(res.status_code, 404)

    def test_unknown_id_404s(self):
        res = self.client.get("/api/store/affiliate/999999/go/")
        self.assertEqual(res.status_code, 404)


# --- Public list: scheduling + placement filters -------------------------


class AffiliatePublicListTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_out_of_window_product_excluded(self):
        make_affiliate_product(title="Expired", ends_at=timezone.now() - timedelta(days=1))
        make_affiliate_product(title="Live", remote_product_id="2")
        res = self.client.get("/api/store/affiliate/")
        titles = [p["title"] for p in res.data["data"]]
        self.assertIn("Live", titles)
        self.assertNotIn("Expired", titles)

    def test_inactive_product_excluded(self):
        make_affiliate_product(title="Off", is_active=False)
        res = self.client.get("/api/store/affiliate/")
        self.assertEqual(res.data["data"], [])

    def test_sidebar_placement_filter(self):
        make_affiliate_product(title="Sidebar item", show_in_sidebar=True)
        make_affiliate_product(title="Not sidebar", remote_product_id="2", show_in_sidebar=False)
        res = self.client.get("/api/store/affiliate/", {"placement": "sidebar"})
        titles = [p["title"] for p in res.data["data"]]
        self.assertEqual(titles, ["Sidebar item"])

    def test_deals_page_placement_filter(self):
        make_affiliate_product(title="Deal item", show_on_deals_page=True)
        make_affiliate_product(title="Not a deal", remote_product_id="2", show_on_deals_page=False)
        res = self.client.get("/api/store/affiliate/", {"placement": "deals"})
        titles = [p["title"] for p in res.data["data"]]
        self.assertEqual(titles, ["Deal item"])

    def test_category_grid_placement_filter(self):
        owner = Users.objects.create_user(
            username="cat-owner", email="cato@x.com", password="x",
            role="Super Admin", country="Bangladesh")
        cat = Categories.objects.create(
            name="Beauty", slug="beauty-health", description="d",
            domain_user_id=owner, added_by_user_id=owner)
        other_cat = Categories.objects.create(
            name="Phones", slug="phones", description="d",
            domain_user_id=owner, added_by_user_id=owner)

        in_cat = make_affiliate_product(title="In beauty grid", show_in_category_grid=True)
        in_cat.grid_categories.add(cat)
        other = make_affiliate_product(title="Not tagged", remote_product_id="2")

        res = self.client.get("/api/store/affiliate/", {"category": "beauty-health"})
        titles = [p["title"] for p in res.data["data"]]
        self.assertEqual(titles, ["In beauty grid"])

        res = self.client.get("/api/store/affiliate/", {"category": "phones"})
        self.assertEqual(res.data["data"], [])

    def test_one_product_can_be_sidebar_only_while_another_is_everywhere(self):
        sidebar_only = make_affiliate_product(
            title="Sidebar only", show_in_sidebar=True, show_on_deals_page=False)
        everywhere = make_affiliate_product(
            title="Everywhere", remote_product_id="2",
            show_in_sidebar=True, show_on_deals_page=True)

        sidebar_titles = [p["title"] for p in self.client.get(
            "/api/store/affiliate/", {"placement": "sidebar"}).data["data"]]
        deals_titles = [p["title"] for p in self.client.get(
            "/api/store/affiliate/", {"placement": "deals"}).data["data"]]

        self.assertIn("Sidebar only", sidebar_titles)
        self.assertIn("Everywhere", sidebar_titles)
        self.assertNotIn("Sidebar only", deals_titles)
        self.assertIn("Everywhere", deals_titles)

    def test_go_url_points_at_our_own_redirect_endpoint(self):
        product = make_affiliate_product()
        res = self.client.get("/api/store/affiliate/")
        go_url = res.data["data"][0]["go_url"]
        self.assertIn(f"/api/store/affiliate/{product.id}/go/", go_url)

    def test_partner_label_present_for_badging(self):
        make_affiliate_product()
        res = self.client.get("/api/store/affiliate/")
        self.assertEqual(res.data["data"][0]["program_label"], "Rokomari")


# --- Admin authorization ---------------------------------------------------


class AffiliateAdminAuthorizationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = Users.objects.create_user(
            username="aff-admin", email="aa@x.com", password="x", role="Admin", country="Bangladesh")
        self.customer = Users.objects.create_user(
            username="aff-cust", email="ac@x.com", password="x", role="Customer", country="Bangladesh")
        self.product = make_affiliate_product()

    def test_customer_403_on_list(self):
        auth(self.client, self.customer)
        res = self.client.get("/api/store/admin/affiliate/")
        self.assertEqual(res.status_code, 403)

    def test_customer_403_on_create(self):
        auth(self.client, self.customer)
        res = self.client.post("/api/store/admin/affiliate/", {
            "remote_product_id": "1", "source_url": "https://www.rokomari.com/product/1/x",
            "title": "X",
        }, format="json")
        self.assertEqual(res.status_code, 403)

    def test_customer_403_on_detail(self):
        auth(self.client, self.customer)
        res = self.client.patch(f"/api/store/admin/affiliate/{self.product.id}/", {"title": "y"}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_customer_403_on_delete(self):
        auth(self.client, self.customer)
        res = self.client.delete(f"/api/store/admin/affiliate/{self.product.id}/")
        self.assertEqual(res.status_code, 403)

    def test_customer_403_on_reorder(self):
        auth(self.client, self.customer)
        res = self.client.post("/api/store/admin/affiliate/reorder/", {"order": [self.product.id]}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_customer_403_on_search(self):
        auth(self.client, self.customer)
        res = self.client.get("/api/store/admin/affiliate/search/", {"q": "perfume"})
        self.assertEqual(res.status_code, 403)

    def test_customer_403_on_bulk_add(self):
        auth(self.client, self.customer)
        res = self.client.post("/api/store/admin/affiliate/bulk-add/", {"candidates": []}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_anonymous_401_or_403_on_list(self):
        res = self.client.get("/api/store/admin/affiliate/")
        self.assertIn(res.status_code, (401, 403))

    def test_admin_can_list(self):
        auth(self.client, self.admin)
        res = self.client.get("/api/store/admin/affiliate/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data["data"]), 1)

    def test_admin_can_update_placement_and_schedule(self):
        auth(self.client, self.admin)
        res = self.client.patch(f"/api/store/admin/affiliate/{self.product.id}/", {
            "show_in_sidebar": True, "link_type": "PRODUCT",
        }, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.product.refresh_from_db()
        self.assertTrue(self.product.show_in_sidebar)
        self.assertEqual(self.product.link_type, "PRODUCT")

    def test_admin_can_delete(self):
        auth(self.client, self.admin)
        res = self.client.delete(f"/api/store/admin/affiliate/{self.product.id}/")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(AffiliateProduct.objects.filter(pk=self.product.id).exists())

    def test_admin_can_reorder(self):
        second = make_affiliate_product(title="Second", remote_product_id="2", display_order=1)
        auth(self.client, self.admin)
        res = self.client.post(
            "/api/store/admin/affiliate/reorder/",
            {"order": [second.id, self.product.id]}, format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        second.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(second.display_order, 0)
        self.assertEqual(self.product.display_order, 1)


# --- Admin search + bulk-add (reuse of the rokomari adapter) --------------


ROKOMARI_LISTING = """<html><body>
<div class="product-card-wrapper"><a href="/product/531074/perfume-a">Perfume A</a></div>
<div class="product-card-wrapper"><a href="/product/531075/perfume-b">Perfume B</a></div>
</body></html>"""


def _rokomari_product_page(name, original_price, current_price):
    return f"""<html><body>
<h1 class="title">{name}</h1>
<div class="details-stationary__price">
    <span class="sell-price">TK.{current_price}</span>
    <strike class="original-price">TK. {original_price}</strike>
</div>
<div class="details-stationary__brand"><a href="/brand/1">TestBrand</a></div>
<div class="details-stationary__thumbnil">
    <ul><li hovermax="https://rokbucket.rokomari.io/x/full.jpg">
        <img src="https://rokbucket.rokomari.io/x/thumb.jpg">
    </li></ul>
</div>
</body></html>"""


class AffiliateAdminSearchAndBulkAddTests(TestCase):
    """No network: polite_get is patched at the same module attribute the
    existing rokomari import flow patches (catalog.test_import_sources.py)."""

    def setUp(self):
        self.client = APIClient()
        self.admin = Users.objects.create_user(
            username="aff-search-admin", email="asa@x.com", password="x",
            role="Admin", country="Bangladesh")
        auth(self.client, self.admin)

    def test_search_returns_candidates_with_remote_product_id(self):
        def fake_fetch(url):
            if "/search" in url:
                return ROKOMARI_LISTING
            return _rokomari_product_page("Perfume A", 590, 554)

        with patch("catalog.services_scrape_import.polite_get", side_effect=fake_fetch):
            res = self.client.get("/api/store/admin/affiliate/search/", {"q": "perfume"})

        self.assertEqual(res.status_code, 200, res.content)
        candidates = res.data["data"]["candidates"]
        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0]["remote_product_id"], "531074")

    def test_search_requires_category_or_query(self):
        res = self.client.get("/api/store/admin/affiliate/search/")
        self.assertEqual(res.status_code, 400)

    def test_bulk_add_creates_products_and_rehosts_image(self):
        payload = {"candidates": [{
            "source_url": "https://www.rokomari.com/product/531074/perfume-a",
            "name": "Perfume A", "brand": "TestBrand",
            "price": 590, "discount_price": 554,
            "images": ["https://rokbucket.rokomari.io/x/full.jpg"],
            "link_type": "CART",
        }]}
        with patch("storefront.views_affiliate.import_image", return_value="/api/media/deadbeef/"):
            res = self.client.post("/api/store/admin/affiliate/bulk-add/", payload, format="json")

        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(len(res.data["data"]["created"]), 1)
        product = AffiliateProduct.objects.get(pk=res.data["data"]["created"][0])
        self.assertEqual(product.remote_product_id, "531074")
        self.assertEqual(product.image, "/api/media/deadbeef/")
        self.assertEqual(product.program, "rokomari")

    def test_bulk_add_skips_already_added_product(self):
        make_affiliate_product(remote_product_id="531074")
        payload = {"candidates": [{
            "source_url": "https://www.rokomari.com/product/531074/perfume-a",
            "name": "Perfume A", "price": 590,
        }]}
        res = self.client.post("/api/store/admin/affiliate/bulk-add/", payload, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.data["data"]["created"], [])
        self.assertEqual(len(res.data["data"]["skipped"]), 1)

    def test_bulk_add_rejects_over_cap_batch(self):
        payload = {"candidates": [
            {"source_url": f"https://www.rokomari.com/product/{i}/item", "name": f"Item {i}", "price": 100}
            for i in range(13)
        ]}
        res = self.client.post("/api/store/admin/affiliate/bulk-add/", payload, format="json")
        self.assertEqual(res.status_code, 400)
