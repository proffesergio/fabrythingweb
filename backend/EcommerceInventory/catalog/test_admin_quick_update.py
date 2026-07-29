"""Admin inline quick-update endpoint for the all-products list.

PATCH /api/products/admin/<pk>/quick-update/ patches only the "quick" fields
(initial_selling_price, discount_price, status, stock_quantity) without
sending the caller through the full product edit form.

Exercised directly against the view via APIRequestFactory + force_authenticate
(see catalog/test_price_sync.py::AdminSyncPricesViewTests for why: going
through the full HTTP client would route the request through
core.middleware.PermissionMiddleware, which blocks any non-platform-scope
user before the view's own isPlatformScope check ever runs, since there is no
ModuleUrls row for this endpoint).
"""
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Users
from catalog.controllers.ProductController import AdminProductQuickUpdateView
from catalog.models import Categories, Products, ProductVariant


class AdminQuickUpdateTestBase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.owner = Users.objects.create_user(
            username="root", email="root@x.com", password="x",
            role="Super Admin", country="Bangladesh")
        self.staff = Users.objects.create_user(
            username="staff", email="staff@x.com", password="x",
            role="Staff", country="Bangladesh", domain_user_id=self.owner)
        self.cat = Categories.objects.create(name="Shirts", slug="qu-shirts", description="")
        self.product = Products.objects.create(
            name="Quick Update Tee", slug="quick-update-tee", sku="QU-0001",
            category_id=self.cat, status="ACTIVE", description="",
            initial_buying_price=100, initial_selling_price=500,
            domain_user_id=self.owner, added_by_user_id=self.owner)
        self.variant = ProductVariant.objects.create(
            product=self.product, sku="QU-0001-DEF", price=500, stock_quantity=10)

    def patch(self, product, data, user):
        request = self.factory.patch(
            f"/api/products/admin/{product.id}/quick-update/", data, format="json")
        force_authenticate(request, user=user)
        return AdminProductQuickUpdateView.as_view()(request, pk=product.id)


class QuickUpdateFieldTests(AdminQuickUpdateTestBase):
    def test_updates_selling_price(self):
        res = self.patch(self.product, {"initial_selling_price": 650}, self.owner)
        self.assertEqual(res.status_code, 200, res.data)
        self.product.refresh_from_db()
        self.assertEqual(self.product.initial_selling_price, 650)

    def test_updates_discount_price(self):
        res = self.patch(self.product, {"discount_price": 400}, self.owner)
        self.assertEqual(res.status_code, 200, res.data)
        self.product.refresh_from_db()
        self.assertEqual(self.product.discount_price, 400)

    def test_clears_discount_price_with_null(self):
        self.product.discount_price = 300
        self.product.save(update_fields=["discount_price"])
        res = self.patch(self.product, {"discount_price": None}, self.owner)
        self.assertEqual(res.status_code, 200, res.data)
        self.product.refresh_from_db()
        self.assertIsNone(self.product.discount_price)

    def test_updates_status_availability(self):
        res = self.patch(self.product, {"status": "INACTIVE"}, self.owner)
        self.assertEqual(res.status_code, 200, res.data)
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, "INACTIVE")

    def test_updates_stock_for_single_variant_product(self):
        res = self.patch(self.product, {"stock_quantity": 42}, self.owner)
        self.assertEqual(res.status_code, 200, res.data)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 42)

    def test_updates_stock_via_explicit_variant_id(self):
        res = self.patch(
            self.product,
            {"stock_quantity": 17, "variant_id": self.variant.id}, self.owner)
        self.assertEqual(res.status_code, 200, res.data)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 17)


class QuickUpdateValidationTests(AdminQuickUpdateTestBase):
    def test_zero_price_rejected(self):
        res = self.patch(self.product, {"initial_selling_price": 0}, self.owner)
        self.assertEqual(res.status_code, 400)
        self.assertIn("initial_selling_price", res.data["field_errors"])
        self.product.refresh_from_db()
        self.assertEqual(self.product.initial_selling_price, 500)

    def test_negative_price_rejected(self):
        res = self.patch(self.product, {"initial_selling_price": -10}, self.owner)
        self.assertEqual(res.status_code, 400)
        self.assertIn("initial_selling_price", res.data["field_errors"])

    def test_discount_above_selling_price_rejected(self):
        res = self.patch(self.product, {"discount_price": 999}, self.owner)
        self.assertEqual(res.status_code, 400)
        self.assertIn("discount_price", res.data["field_errors"])
        self.product.refresh_from_db()
        self.assertIsNone(self.product.discount_price)

    def test_discount_above_new_selling_price_rejected(self):
        # Both fields sent together: discount is validated against the NEW
        # selling price, not the stale one still on the row.
        res = self.patch(
            self.product,
            {"initial_selling_price": 300, "discount_price": 350}, self.owner)
        self.assertEqual(res.status_code, 400)
        self.assertIn("discount_price", res.data["field_errors"])
        self.product.refresh_from_db()
        self.assertEqual(self.product.initial_selling_price, 500)

    def test_invalid_status_rejected(self):
        res = self.patch(self.product, {"status": "DELETED"}, self.owner)
        self.assertEqual(res.status_code, 400)
        self.assertIn("status", res.data["field_errors"])

    def test_stock_without_variant_id_on_multi_variant_product_rejected(self):
        ProductVariant.objects.create(
            product=self.product, sku="QU-0001-LG", size="L", price=500, stock_quantity=5)
        res = self.patch(self.product, {"stock_quantity": 20}, self.owner)
        self.assertEqual(res.status_code, 400)
        self.assertIn("variant_id", res.data["field_errors"])

    def test_unknown_product_404(self):
        res = self.patch_missing()
        self.assertEqual(res.status_code, 404)

    def patch_missing(self):
        request = self.factory.patch(
            "/api/products/admin/999999/quick-update/",
            {"status": "INACTIVE"}, format="json")
        force_authenticate(request, user=self.owner)
        return AdminProductQuickUpdateView.as_view()(request, pk=999999)


class QuickUpdateAuthorizationTests(AdminQuickUpdateTestBase):
    def test_non_platform_user_forbidden(self):
        res = self.patch(self.product, {"status": "INACTIVE"}, self.staff)
        self.assertEqual(res.status_code, 403)
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, "ACTIVE")


class QuickUpdatePriceVariantConsistencyTests(AdminQuickUpdateTestBase):
    def test_variant_price_stays_in_sync_after_price_update(self):
        # CRITICAL: checkout charges ProductVariant.effective_price, not the
        # Products fields (see catalog/services_price_sync.py). A quick-edit
        # that only touches Products would let the storefront show one price
        # while checkout charges another.
        res = self.patch(
            self.product,
            {"initial_selling_price": 700, "discount_price": 600}, self.owner)
        self.assertEqual(res.status_code, 200, res.data)
        self.variant.refresh_from_db()
        self.assertEqual(float(self.variant.price), 700)
        self.assertEqual(float(self.variant.discount_price), 600)
        self.assertEqual(float(self.variant.effective_price), 600)

    def test_inactive_variants_are_not_repriced(self):
        self.variant.is_active = False
        self.variant.save(update_fields=["is_active"])
        res = self.patch(self.product, {"initial_selling_price": 700}, self.owner)
        self.assertEqual(res.status_code, 200, res.data)
        self.variant.refresh_from_db()
        self.assertEqual(float(self.variant.price), 500)
