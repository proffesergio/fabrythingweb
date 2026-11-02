"""Admin shipping-fee editing:
- PATCH /api/products/admin/<pk>/quick-update/ accepting `shipping_fee`
  (extending the existing quick-update endpoint).
- POST /api/products/admin/shipping-fee/bulk/ (new) to set the same fee on
  many products at once, by explicit id list or by category subtree.

Exercised via APIRequestFactory + force_authenticate rather than the full
HTTP client, same reasoning as catalog/test_admin_quick_update.py: going
through the real client routes the request through
core.middleware.PermissionMiddleware, which blocks non-platform-scope users
before the view's own isPlatformScope check ever gets a chance to run (no
ModuleUrls row exists for these endpoints).
"""
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Users
from catalog.controllers.ProductController import (
    AdminBulkShippingFeeView,
    AdminProductQuickUpdateView,
)
from catalog.models import Categories, Products, ProductVariant


def make_product(cat, owner, slug, name="Product", price=500):
    return Products.objects.create(
        name=name, slug=slug, sku=slug.upper(), category_id=cat, status="ACTIVE",
        description="", initial_buying_price=price, initial_selling_price=price,
        domain_user_id=owner, added_by_user_id=owner,
    )


class ShippingFeeTestBase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.owner = Users.objects.create_user(
            username="root2", email="root2@x.com", password="x",
            role="Super Admin", country="Bangladesh")
        self.staff = Users.objects.create_user(
            username="staff2", email="staff2@x.com", password="x",
            role="Staff", country="Bangladesh", domain_user_id=self.owner)
        self.cat = Categories.objects.create(name="Shirts2", slug="sfa-shirts", description="")


class QuickUpdateShippingFeeTests(ShippingFeeTestBase):
    def setUp(self):
        super().setUp()
        self.product = make_product(self.cat, self.owner, "sfa-tee")

    def patch(self, data, user=None):
        request = self.factory.patch(
            f"/api/products/admin/{self.product.id}/quick-update/", data, format="json")
        force_authenticate(request, user=user or self.owner)
        return AdminProductQuickUpdateView.as_view()(request, pk=self.product.id)

    def test_sets_shipping_fee(self):
        res = self.patch({"shipping_fee": 250})
        self.assertEqual(res.status_code, 200, res.data)
        self.product.refresh_from_db()
        self.assertEqual(float(self.product.shipping_fee), 250.0)

    def test_sets_explicit_zero_shipping_fee(self):
        res = self.patch({"shipping_fee": 0})
        self.assertEqual(res.status_code, 200, res.data)
        self.product.refresh_from_db()
        self.assertEqual(float(self.product.shipping_fee), 0.0)
        self.assertIsNotNone(self.product.shipping_fee)

    def test_clears_shipping_fee_with_null(self):
        self.product.shipping_fee = 100
        self.product.save(update_fields=["shipping_fee"])
        res = self.patch({"shipping_fee": None})
        self.assertEqual(res.status_code, 200, res.data)
        self.product.refresh_from_db()
        self.assertIsNone(self.product.shipping_fee)

    def test_negative_shipping_fee_rejected(self):
        res = self.patch({"shipping_fee": -10})
        self.assertEqual(res.status_code, 400)
        self.assertIn("shipping_fee", res.data["field_errors"])
        self.product.refresh_from_db()
        self.assertIsNone(self.product.shipping_fee)

    def test_non_numeric_shipping_fee_rejected(self):
        res = self.patch({"shipping_fee": "abc"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("shipping_fee", res.data["field_errors"])

    def test_non_platform_user_forbidden(self):
        res = self.patch({"shipping_fee": 250}, user=self.staff)
        self.assertEqual(res.status_code, 403)
        self.product.refresh_from_db()
        self.assertIsNone(self.product.shipping_fee)

    def test_sets_free_shipping_promo_flag(self):
        res = self.patch({"free_shipping": True})
        self.assertEqual(res.status_code, 200, res.data)
        self.product.refresh_from_db()
        self.assertTrue(self.product.free_shipping)
        self.assertTrue(res.data["data"]["free_shipping"])

    def test_clears_free_shipping_promo_flag(self):
        self.product.free_shipping = True
        self.product.save(update_fields=["free_shipping"])
        res = self.patch({"free_shipping": False})
        self.assertEqual(res.status_code, 200, res.data)
        self.product.refresh_from_db()
        self.assertFalse(self.product.free_shipping)

    def test_non_boolean_free_shipping_rejected(self):
        res = self.patch({"free_shipping": "yes"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("free_shipping", res.data["field_errors"])
        self.product.refresh_from_db()
        self.assertFalse(self.product.free_shipping)

    def test_free_shipping_non_platform_user_forbidden(self):
        res = self.patch({"free_shipping": True}, user=self.staff)
        self.assertEqual(res.status_code, 403)
        self.product.refresh_from_db()
        self.assertFalse(self.product.free_shipping)


class BulkShippingFeeTests(ShippingFeeTestBase):
    def setUp(self):
        super().setUp()
        self.p1 = make_product(self.cat, self.owner, "sfa-p1")
        self.p2 = make_product(self.cat, self.owner, "sfa-p2")
        self.other_cat = Categories.objects.create(name="Other", slug="sfa-other", description="")
        self.p3 = make_product(self.other_cat, self.owner, "sfa-p3")

    def bulk(self, data, user=None):
        request = self.factory.post(
            "/api/products/admin/shipping-fee/bulk/", data, format="json")
        force_authenticate(request, user=user or self.owner)
        return AdminBulkShippingFeeView.as_view()(request)

    def test_sets_fee_on_explicit_product_ids(self):
        res = self.bulk({"shipping_fee": 150, "product_ids": [self.p1.id, self.p2.id]})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["data"]["updated"], 2)
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.p3.refresh_from_db()
        self.assertEqual(float(self.p1.shipping_fee), 150.0)
        self.assertEqual(float(self.p2.shipping_fee), 150.0)
        self.assertIsNone(self.p3.shipping_fee)

    def test_sets_fee_on_whole_category_subtree(self):
        # Category tree: sfa-shirts (parent) -> sfa-child (leaf product lives here)
        child = Categories.objects.create(name="Child", slug="sfa-child", parent_id=self.cat, description="")
        leaf_product = make_product(child, self.owner, "sfa-leaf")

        res = self.bulk({"shipping_fee": 90, "category": self.cat.slug})
        self.assertEqual(res.status_code, 200, res.data)
        # p1, p2 (direct) + leaf_product (grandchild) = 3 rows, not p3 (other_cat).
        self.assertEqual(res.data["data"]["updated"], 3)
        leaf_product.refresh_from_db()
        self.p3.refresh_from_db()
        self.assertEqual(float(leaf_product.shipping_fee), 90.0)
        self.assertIsNone(self.p3.shipping_fee)

    def test_category_by_numeric_id_also_works(self):
        res = self.bulk({"shipping_fee": 90, "category": str(self.cat.id)})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["data"]["updated"], 2)

    def test_clearing_fee_with_null_across_a_bulk_selection(self):
        Products.objects.filter(id__in=[self.p1.id, self.p2.id]).update(shipping_fee=200)
        res = self.bulk({"shipping_fee": None, "product_ids": [self.p1.id, self.p2.id]})
        self.assertEqual(res.status_code, 200, res.data)
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertIsNone(self.p1.shipping_fee)
        self.assertIsNone(self.p2.shipping_fee)

    def test_negative_fee_rejected(self):
        res = self.bulk({"shipping_fee": -5, "product_ids": [self.p1.id]})
        self.assertEqual(res.status_code, 400)
        self.assertIn("shipping_fee", res.data["field_errors"])

    def test_unknown_category_rejected(self):
        res = self.bulk({"shipping_fee": 50, "category": "does-not-exist"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("category", res.data["field_errors"])

    def test_missing_selection_rejected(self):
        res = self.bulk({"shipping_fee": 50})
        self.assertEqual(res.status_code, 400)
        self.assertIn("product_ids", res.data["field_errors"])

    def test_both_selectors_at_once_rejected(self):
        res = self.bulk({"shipping_fee": 50, "product_ids": [self.p1.id], "category": self.cat.slug})
        self.assertEqual(res.status_code, 400)
        self.assertIn("product_ids", res.data["field_errors"])

    def test_batch_over_cap_is_rejected(self):
        original_cap = AdminBulkShippingFeeView.MAX_BATCH
        AdminBulkShippingFeeView.MAX_BATCH = 1
        try:
            res = self.bulk({"shipping_fee": 50, "product_ids": [self.p1.id, self.p2.id]})
            self.assertEqual(res.status_code, 400)
            self.assertIn("product_ids", res.data["field_errors"])
        finally:
            AdminBulkShippingFeeView.MAX_BATCH = original_cap
        self.p1.refresh_from_db()
        self.assertIsNone(self.p1.shipping_fee)

    def test_non_platform_user_forbidden(self):
        res = self.bulk({"shipping_fee": 50, "product_ids": [self.p1.id]}, user=self.staff)
        self.assertEqual(res.status_code, 403)
        self.p1.refresh_from_db()
        self.assertIsNone(self.p1.shipping_fee)

    def test_sets_free_shipping_on_explicit_product_ids(self):
        res = self.bulk({
            "shipping_fee": None, "free_shipping": True,
            "product_ids": [self.p1.id, self.p2.id],
        })
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["data"]["updated"], 2)
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.p3.refresh_from_db()
        self.assertTrue(self.p1.free_shipping)
        self.assertTrue(self.p2.free_shipping)
        self.assertFalse(self.p3.free_shipping)

    def test_sets_free_shipping_on_whole_category_subtree(self):
        child = Categories.objects.create(name="Child2", slug="sfa-child2", parent_id=self.cat, description="")
        leaf_product = make_product(child, self.owner, "sfa-leaf2")

        res = self.bulk({"free_shipping": True, "category": self.cat.slug})
        self.assertEqual(res.status_code, 200, res.data)
        # p1, p2 (direct) + leaf_product (grandchild) = 3 rows, not p3 (other_cat).
        self.assertEqual(res.data["data"]["updated"], 3)
        leaf_product.refresh_from_db()
        self.p3.refresh_from_db()
        self.assertTrue(leaf_product.free_shipping)
        self.assertFalse(self.p3.free_shipping)

    def test_free_shipping_alone_without_shipping_fee_key_is_allowed(self):
        # The owner should be able to promo a category as free-shipping
        # without also having to specify a numeric shipping_fee.
        res = self.bulk({"free_shipping": True, "product_ids": [self.p1.id]})
        self.assertEqual(res.status_code, 200, res.data)
        self.p1.refresh_from_db()
        self.assertTrue(self.p1.free_shipping)
        self.assertIsNone(self.p1.shipping_fee)

    def test_non_boolean_free_shipping_rejected_in_bulk(self):
        res = self.bulk({"free_shipping": "yes", "product_ids": [self.p1.id]})
        self.assertEqual(res.status_code, 400)
        self.assertIn("free_shipping", res.data["field_errors"])
        self.p1.refresh_from_db()
        self.assertFalse(self.p1.free_shipping)

    def test_neither_shipping_fee_nor_free_shipping_rejected(self):
        res = self.bulk({"product_ids": [self.p1.id]})
        self.assertEqual(res.status_code, 400)
        self.assertIn("shipping_fee", res.data["field_errors"])

    def test_free_shipping_non_platform_user_forbidden(self):
        res = self.bulk({"free_shipping": True, "product_ids": [self.p1.id]}, user=self.staff)
        self.assertEqual(res.status_code, 403)
        self.p1.refresh_from_db()
        self.assertFalse(self.p1.free_shipping)
