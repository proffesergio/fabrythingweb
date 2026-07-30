"""Regression tests for the isPlatformScope-as-authorization vulnerability.

core.helpers.isPlatformScope(user) returns True for ANY domain-root user, not
only staff -- and Users.save() self-assigns domain_user_id = self.id for
every account created without one, including every customer who
self-signs-up at /api/store/auth/signup/ (and every Rider/Restaurant created
through their own onboarding flows). That made isPlatformScope alone true for
a plain Customer/Rider/Restaurant, and every admin catalog endpoint below
used isPlatformScope alone as its authorization check -- so a self-signed-up
Customer could list the full admin product catalog (leaking base_price,
source_price, source_url, initial_buying_price) and could sync/quick-update/
bulk-edit prices and shipping fees, and browse/import products.

core.helpers.isPlatformStaff (role in Admin/Super Admin/Staff AND
isPlatformScope) is the fix -- see core/test_helpers.py for the unit tests on
the helper itself. This file pins the fix at every affected endpoint.
"""
from django.test import TestCase
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Users
from catalog.controllers.CategoryController import CategoryListView
from catalog.controllers.ProductController import (
    AdminBulkShippingFeeView,
    AdminProductQuickUpdateView,
    AdminSyncPricesView,
)
from catalog.controllers.ProductImportController import (
    AdminBrowseImportCandidatesView,
    AdminImportProductsView,
)
from catalog.models import Categories, Products, ProductVariant


def auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")


class AdminAuthorizationTestBase(TestCase):
    """Every self-signed-up-style account below is its own domain root
    (domain_user_id_id == id) exactly like a real /api/store/auth/signup/
    Customer -- Users.objects.create_user with no domain_user_id kwarg
    reproduces that self-heal path faithfully."""

    def setUp(self):
        self.client = APIClient()
        self.factory = APIRequestFactory()

        self.super_admin = Users.objects.create_user(
            username="platform-super", email="platform-super@x.com", password="x",
            role="Super Admin", country="Bangladesh")
        self.domain_admin = Users.objects.create_user(
            username="platform-admin", email="platform-admin@x.com", password="x",
            role="Admin", country="Bangladesh")
        # A domain sub-account: legitimate back-office role, but NOT platform
        # scope (must stay 403 on the platform-only endpoints, same as before).
        self.sub_staff = Users.objects.create_user(
            username="sub-staff", email="sub-staff@x.com", password="x",
            role="Staff", country="Bangladesh", domain_user_id=self.super_admin)

        self.customer = Users.objects.create_user(
            username="self-signup-customer", email="customer@x.com", password="x",
            role="Customer", country="Bangladesh")
        self.rider = Users.objects.create_user(
            username="self-signup-rider", email="rider@x.com", password="x",
            role="Rider", country="Bangladesh")
        self.restaurant = Users.objects.create_user(
            username="self-signup-restaurant", email="restaurant@x.com", password="x",
            role="Restaurant", country="Bangladesh")

        self.assertEqual(self.customer.domain_user_id_id, self.customer.id)
        self.assertEqual(self.rider.domain_user_id_id, self.rider.id)
        self.assertEqual(self.restaurant.domain_user_id_id, self.restaurant.id)

        self.cat = Categories.objects.create(
            name="Auth Test Cat", slug="auth-test-cat", description="",
            domain_user_id=self.super_admin, added_by_user_id=self.super_admin)
        self.product = Products.objects.create(
            name="Auth Test Product", slug="auth-test-product", sku="AUTH-0001",
            category_id=self.cat, status="ACTIVE", description="",
            initial_buying_price=100, initial_selling_price=500,
            source_url="https://potakait.com/auth-test", source_price=480,
            domain_user_id=self.super_admin, added_by_user_id=self.super_admin)
        ProductVariant.objects.create(
            product=self.product, sku="AUTH-0001-DEF", price=500, stock_quantity=10)

    @property
    def non_staff_roles(self):
        return (self.customer, self.rider, self.restaurant)


class AdminProductListLeakTests(AdminAuthorizationTestBase):
    """GET /api/products/ -- the confidential-data leak (base_price,
    source_price, source_url, initial_buying_price)."""

    def test_customer_gets_403_not_the_catalog(self):
        auth(self.client, self.customer)
        res = self.client.get("/api/products/")
        self.assertEqual(res.status_code, 403, res.content)

    def test_rider_gets_403(self):
        auth(self.client, self.rider)
        res = self.client.get("/api/products/")
        self.assertEqual(res.status_code, 403, res.content)

    def test_restaurant_gets_403(self):
        auth(self.client, self.restaurant)
        res = self.client.get("/api/products/")
        self.assertEqual(res.status_code, 403, res.content)

    def test_super_admin_still_sees_the_catalog(self):
        auth(self.client, self.super_admin)
        res = self.client.get("/api/products/")
        self.assertEqual(res.status_code, 200, res.content)
        slugs = [r["slug"] for r in res.json()["data"]["data"]]
        self.assertIn("auth-test-product", slugs)

    def test_domain_root_admin_still_sees_the_catalog(self):
        auth(self.client, self.domain_admin)
        res = self.client.get("/api/products/")
        self.assertEqual(res.status_code, 200, res.content)

    def test_sub_domain_staff_still_sees_their_own_domain_catalog(self):
        # Regression guard: a legitimate back-office Staff sub-account (not a
        # domain root) must keep seeing their own tenant's products, scoped
        # by domain -- this must not turn into a blanket 403 for real staff.
        # Exercised directly against the view (APIRequestFactory +
        # force_authenticate): going through the full HTTP client would route
        # through core.middleware.PermissionMiddleware, which blocks a
        # non-domain-root user with 400 "Module not Exist" before the view's
        # own check ever runs, since there is no ModuleUrls row for this
        # endpoint -- same reasoning as catalog/test_price_sync.py.
        from catalog.controllers.ProductController import ProductListView
        request = self.factory.get("/api/products/")
        force_authenticate(request, user=self.sub_staff)
        res = ProductListView.as_view()(request)
        self.assertEqual(res.status_code, 200, res.data)
        # sub_staff's domain is self.super_admin (its owner), and the fixture
        # product also belongs to self.super_admin -- so it's their own
        # tenant's product, correctly visible through the domain-scoped
        # (non-widened) branch.
        slugs = [r["slug"] for r in res.data["data"]["data"]]
        self.assertIn("auth-test-product", slugs)


class AdminCategoryListTests(AdminAuthorizationTestBase):
    """GET /api/products/categories/"""

    def test_customer_gets_403(self):
        auth(self.client, self.customer)
        res = self.client.get("/api/products/categories/")
        self.assertEqual(res.status_code, 403, res.content)

    def test_rider_gets_403(self):
        auth(self.client, self.rider)
        res = self.client.get("/api/products/categories/")
        self.assertEqual(res.status_code, 403, res.content)

    def test_restaurant_gets_403(self):
        auth(self.client, self.restaurant)
        res = self.client.get("/api/products/categories/")
        self.assertEqual(res.status_code, 403, res.content)

    def test_super_admin_still_works(self):
        auth(self.client, self.super_admin)
        res = self.client.get("/api/products/categories/")
        self.assertEqual(res.status_code, 200, res.content)

    def test_sub_domain_staff_still_works(self):
        # See the comment on AdminProductListLeakTests.
        # test_sub_domain_staff_still_sees_their_own_domain_catalog for why
        # this goes straight to the view instead of the full HTTP client.
        from catalog.controllers.CategoryController import CategoryListView
        request = self.factory.get("/api/products/categories/")
        force_authenticate(request, user=self.sub_staff)
        res = CategoryListView.as_view()(request)
        self.assertEqual(res.status_code, 200, res.data)


class AdminSyncPricesAuthorizationTests(AdminAuthorizationTestBase):
    def _post(self, user):
        request = self.factory.post("/api/products/admin/sync-prices/")
        force_authenticate(request, user=user)
        return AdminSyncPricesView.as_view()(request)

    def test_customer_forbidden(self):
        self.assertEqual(self._post(self.customer).status_code, 403)

    def test_rider_forbidden(self):
        self.assertEqual(self._post(self.rider).status_code, 403)

    def test_restaurant_forbidden(self):
        self.assertEqual(self._post(self.restaurant).status_code, 403)

    def test_super_admin_allowed(self):
        from unittest.mock import patch
        with patch("catalog.controllers.ProductController.sync_source_prices", return_value=[]):
            self.assertEqual(self._post(self.super_admin).status_code, 200)


class AdminQuickUpdateAuthorizationTests(AdminAuthorizationTestBase):
    def _patch(self, user):
        request = self.factory.patch(
            f"/api/products/admin/{self.product.id}/quick-update/",
            {"status": "INACTIVE"}, format="json")
        force_authenticate(request, user=user)
        return AdminProductQuickUpdateView.as_view()(request, pk=self.product.id)

    def test_customer_forbidden(self):
        res = self._patch(self.customer)
        self.assertEqual(res.status_code, 403)
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, "ACTIVE")

    def test_rider_forbidden(self):
        self.assertEqual(self._patch(self.rider).status_code, 403)

    def test_restaurant_forbidden(self):
        self.assertEqual(self._patch(self.restaurant).status_code, 403)

    def test_super_admin_allowed(self):
        self.assertEqual(self._patch(self.super_admin).status_code, 200)


class AdminBulkShippingFeeAuthorizationTests(AdminAuthorizationTestBase):
    def _post(self, user):
        request = self.factory.post(
            "/api/products/admin/shipping-fee/bulk/",
            {"shipping_fee": 50, "product_ids": [self.product.id]}, format="json")
        force_authenticate(request, user=user)
        return AdminBulkShippingFeeView.as_view()(request)

    def test_customer_forbidden(self):
        self.assertEqual(self._post(self.customer).status_code, 403)

    def test_rider_forbidden(self):
        self.assertEqual(self._post(self.rider).status_code, 403)

    def test_restaurant_forbidden(self):
        self.assertEqual(self._post(self.restaurant).status_code, 403)

    def test_super_admin_allowed(self):
        self.assertEqual(self._post(self.super_admin).status_code, 200)


class AdminImportAuthorizationTests(AdminAuthorizationTestBase):
    def _browse(self, user):
        request = self.factory.get(
            "/api/products/admin/import/browse/", {"source": "potakait", "q": "phone"})
        force_authenticate(request, user=user)
        return AdminBrowseImportCandidatesView.as_view()(request)

    def _import(self, user):
        request = self.factory.post(
            "/api/products/admin/import/",
            {"source": "potakait", "source_urls": ["https://potakait.com/x"],
             "category_id": self.cat.id}, format="json")
        force_authenticate(request, user=user)
        return AdminImportProductsView.as_view()(request)

    def test_browse_customer_forbidden(self):
        self.assertEqual(self._browse(self.customer).status_code, 403)

    def test_browse_rider_forbidden(self):
        self.assertEqual(self._browse(self.rider).status_code, 403)

    def test_browse_restaurant_forbidden(self):
        self.assertEqual(self._browse(self.restaurant).status_code, 403)

    def test_import_customer_forbidden(self):
        self.assertEqual(self._import(self.customer).status_code, 403)

    def test_import_rider_forbidden(self):
        self.assertEqual(self._import(self.rider).status_code, 403)

    def test_import_restaurant_forbidden(self):
        self.assertEqual(self._import(self.restaurant).status_code, 403)


class AdminImportSourceManagementAuthorizationTests(AdminAuthorizationTestBase):
    """The DB-driven import control panel (ImportSource/ImportSourceCategory/
    ImportRun admin endpoints, catalog.controllers.ImportSourceController)
    must be gated by the same isPlatformStaff rule as the browse/import pair
    above -- these are equally capable of leaking source config or letting a
    self-signed-up account disable/enable a partner source."""

    def setUp(self):
        super().setUp()
        from catalog.models import ImportSource
        self.potakait = ImportSource.objects.get(slug="potakait")

    def _list_sources(self, user):
        from catalog.controllers.ImportSourceController import AdminImportSourceListCreateView
        request = self.factory.get("/api/products/admin/import/sources/")
        force_authenticate(request, user=user)
        return AdminImportSourceListCreateView.as_view()(request)

    def _patch_source(self, user):
        from catalog.controllers.ImportSourceController import AdminImportSourceDetailView
        request = self.factory.patch(
            f"/api/products/admin/import/sources/{self.potakait.id}/",
            {"is_enabled": False}, format="json")
        force_authenticate(request, user=user)
        return AdminImportSourceDetailView.as_view()(request, pk=self.potakait.id)

    def _run_list(self, user):
        auth(self.client, user)
        return self.client.get("/api/products/admin/import/runs/")

    def test_list_sources_customer_forbidden(self):
        self.assertEqual(self._list_sources(self.customer).status_code, 403)

    def test_list_sources_rider_forbidden(self):
        self.assertEqual(self._list_sources(self.rider).status_code, 403)

    def test_list_sources_restaurant_forbidden(self):
        self.assertEqual(self._list_sources(self.restaurant).status_code, 403)

    def test_patch_source_customer_forbidden(self):
        res = self._patch_source(self.customer)
        self.assertEqual(res.status_code, 403)
        self.potakait.refresh_from_db()
        self.assertTrue(self.potakait.is_enabled)  # unchanged

    def test_run_list_customer_forbidden(self):
        self.assertEqual(self._run_list(self.customer).status_code, 403)

    def test_run_list_rider_forbidden(self):
        self.assertEqual(self._run_list(self.rider).status_code, 403)

    def test_run_list_restaurant_forbidden(self):
        self.assertEqual(self._run_list(self.restaurant).status_code, 403)

    def test_super_admin_allowed_on_sources_and_runs(self):
        self.assertEqual(self._list_sources(self.super_admin).status_code, 200)
        self.assertEqual(self._run_list(self.super_admin).status_code, 200)
