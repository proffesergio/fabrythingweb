"""shipping_fee must be visible to customers: the storefront product list
and detail serializers expose the raw `shipping_fee` (null vs 0 preserved,
so the frontend can tell "no fee set" from "explicitly free") plus a
resolved `effective_shipping_fee` that always falls back to the store's flat
rate, so the customer is never shown nothing.
"""
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Categories, Products
from core.models import StoreConfiguration


class ShippingFeeDisplayTestBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.cat = Categories.objects.create(name="Disp", slug="sfd-cat", description="")
        cfg = StoreConfiguration.get_solo()
        cfg.fixed_shipping_rate = Decimal("60.00")
        cfg.save()


class ProductListSerializerShippingFeeTests(ShippingFeeDisplayTestBase):
    def test_product_with_no_fee_shows_null_raw_and_flat_rate_effective(self):
        Products.objects.create(
            name="No Fee", slug="sfd-nofee", sku="SFD-NOFEE", category_id=self.cat,
            status="ACTIVE", description="", initial_buying_price=100, initial_selling_price=200,
        )
        res = self.client.get("/api/store/products/")
        self.assertEqual(res.status_code, 200, res.content)
        row = next(r for r in res.json()["data"]["data"] if r["slug"] == "sfd-nofee")
        self.assertIsNone(row["shipping_fee"])
        self.assertEqual(row["effective_shipping_fee"], 60.0)

    def test_product_with_explicit_zero_fee_shows_zero_not_null(self):
        Products.objects.create(
            name="Free Ship", slug="sfd-free", sku="SFD-FREE", category_id=self.cat,
            status="ACTIVE", description="", initial_buying_price=100, initial_selling_price=200,
            shipping_fee=Decimal("0"),
        )
        res = self.client.get("/api/store/products/")
        self.assertEqual(res.status_code, 200, res.content)
        row = next(r for r in res.json()["data"]["data"] if r["slug"] == "sfd-free")
        self.assertEqual(row["shipping_fee"], 0.0)
        self.assertEqual(row["effective_shipping_fee"], 0.0)

    def test_product_with_a_fee_shows_it_on_both_fields(self):
        Products.objects.create(
            name="Bulky", slug="sfd-bulky", sku="SFD-BULKY", category_id=self.cat,
            status="ACTIVE", description="", initial_buying_price=1000, initial_selling_price=1500,
            shipping_fee=Decimal("250"),
        )
        res = self.client.get("/api/store/products/")
        self.assertEqual(res.status_code, 200, res.content)
        row = next(r for r in res.json()["data"]["data"] if r["slug"] == "sfd-bulky")
        self.assertEqual(row["shipping_fee"], 250.0)
        self.assertEqual(row["effective_shipping_fee"], 250.0)


class ProductDetailSerializerShippingFeeTests(ShippingFeeDisplayTestBase):
    def test_detail_view_exposes_shipping_fee_fields(self):
        Products.objects.create(
            name="Detail Bulky", slug="sfd-detail-bulky", sku="SFD-DETAIL-BULKY",
            category_id=self.cat, status="ACTIVE", description="",
            initial_buying_price=1000, initial_selling_price=1500, shipping_fee=Decimal("300"),
        )
        res = self.client.get("/api/store/products/sfd-detail-bulky/")
        self.assertEqual(res.status_code, 200, res.content)
        data = res.json()["data"]
        self.assertEqual(data["shipping_fee"], 300.0)
        self.assertEqual(data["effective_shipping_fee"], 300.0)

    def test_detail_view_falls_back_to_flat_rate_when_unset(self):
        Products.objects.create(
            name="Detail Plain", slug="sfd-detail-plain", sku="SFD-DETAIL-PLAIN",
            category_id=self.cat, status="ACTIVE", description="",
            initial_buying_price=100, initial_selling_price=200,
        )
        res = self.client.get("/api/store/products/sfd-detail-plain/")
        self.assertEqual(res.status_code, 200, res.content)
        data = res.json()["data"]
        self.assertIsNone(data["shipping_fee"])
        self.assertEqual(data["effective_shipping_fee"], 60.0)
