"""End-to-end: per-product shipping_fee flowing through the real COD
checkout path (POST /api/store/orders/), which calls
orders.services.place_cod_order -- the single place order shipping is
computed (core.models.StoreConfiguration.shipping_for). These pin the three
worked examples from docs/SHIPPING_FEES.md against the real HTTP endpoint,
not just the unit-level shipping_for tests in core/test_shipping.py.
"""
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Users
from catalog.models import Categories, Products, ProductVariant
from core.models import StoreConfiguration
from orders.models import Order


def make_product(name, slug, sku, price, shipping_fee=None, category=None):
    product = Products.objects.create(
        name=name, slug=slug, sku=sku, category_id=category, status="ACTIVE",
        description="", initial_buying_price=price, initial_selling_price=price,
        shipping_fee=shipping_fee,
    )
    variant = ProductVariant.objects.create(
        product=product, sku=f"{sku}-DEF", price=Decimal(str(price)), stock_quantity=50,
    )
    return product, variant


class CheckoutShippingFeeTestBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.cat = Categories.objects.create(name="Elec", slug="sf-elec", description="")
        cfg = StoreConfiguration.get_solo()
        cfg.fixed_shipping_rate = Decimal("60.00")
        cfg.free_shipping_threshold = None
        cfg.save()

    def place_order(self, items):
        payload = {
            "items": items,
            "shipping_address": {
                "address": "1 Test Rd", "city": "Dhaka",
            },
            "contact_name": "Karim", "contact_phone": "01711112222",
        }
        return self.client.post("/api/store/orders/", payload, format="json")


class HighestFeeWinsTests(CheckoutShippingFeeTestBase):
    def test_highest_per_product_fee_among_cart_items_is_charged(self):
        # Worked example 1: 60-flat shirt + monitor with a 250 fee -> 250.
        shirt, shirt_variant = make_product(
            "Shirt", "sf-shirt", "SF-SHIRT", 500, shipping_fee=None, category=self.cat)
        monitor, monitor_variant = make_product(
            "Monitor", "sf-monitor", "SF-MON", 15000, shipping_fee=Decimal("250"), category=self.cat)

        res = self.place_order([
            {"variant_id": shirt_variant.id, "quantity": 1},
            {"variant_id": monitor_variant.id, "quantity": 1},
        ])
        self.assertEqual(res.status_code, 201, res.content)
        order = Order.objects.get(order_number=res.json()["data"]["order_number"])
        self.assertEqual(order.shipping_amount, Decimal("250.00"))
        self.assertEqual(res.json()["data"]["shipping_amount"], 250.0)


class NoFeesFallsBackToFlatRateTests(CheckoutShippingFeeTestBase):
    def test_two_products_no_fees_uses_flat_rate_unchanged(self):
        # Worked example 2: two products, no per-product fees -> flat rate,
        # exactly as it behaved before this feature.
        p1, v1 = make_product("A", "sf-a", "SF-A", 300, category=self.cat)
        p2, v2 = make_product("B", "sf-b", "SF-B", 400, category=self.cat)

        res = self.place_order([
            {"variant_id": v1.id, "quantity": 1},
            {"variant_id": v2.id, "quantity": 1},
        ])
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()["data"]["shipping_amount"], 60.0)


class LowFeeDoesNotUndercutFlatRateTests(CheckoutShippingFeeTestBase):
    def test_fee_below_flat_rate_still_charges_flat_rate(self):
        # Worked example 3: one product with a 30 fee, flat rate 60 -> 60.
        p, v = make_product("Cheap-ship item", "sf-cheap", "SF-CHEAP", 200,
                            shipping_fee=Decimal("30"), category=self.cat)

        res = self.place_order([{"variant_id": v.id, "quantity": 1}])
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()["data"]["shipping_amount"], 60.0)


class FreeShippingThresholdStillHonouredTests(CheckoutShippingFeeTestBase):
    def setUp(self):
        super().setUp()
        cfg = StoreConfiguration.get_solo()
        cfg.free_shipping_threshold = Decimal("1000.00")
        cfg.save()

    def test_subtotal_over_threshold_ships_free_even_with_a_product_fee(self):
        p, v = make_product("Bulky", "sf-bulky", "SF-BULKY", 5000,
                            shipping_fee=Decimal("250"), category=self.cat)

        res = self.place_order([{"variant_id": v.id, "quantity": 1}])
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()["data"]["shipping_amount"], 0.0)

    def test_subtotal_under_threshold_still_uses_max_rule(self):
        p, v = make_product("Bulky2", "sf-bulky2", "SF-BULKY2", 200,
                            shipping_fee=Decimal("250"), category=self.cat)

        res = self.place_order([{"variant_id": v.id, "quantity": 1}])
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()["data"]["shipping_amount"], 250.0)
