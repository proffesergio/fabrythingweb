"""End-to-end: Products.requires_prescription flowing through the real COD
checkout path (POST /api/store/orders/), which calls
orders.services.place_cod_order -- the single place a cart/line is validated,
so this is the one guard no endpoint can bypass. Gated behind
core.models.StoreConfiguration.rx_sales_enabled (default False -- the owner
does not yet hold a DGDA licence).
"""
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Categories, Products, ProductVariant
from core.models import StoreConfiguration
from orders.models import Order


def make_product(name, slug, sku, price, category, requires_prescription=False):
    product = Products.objects.create(
        name=name, slug=slug, sku=sku, category_id=category, status="ACTIVE",
        description="", initial_buying_price=price, initial_selling_price=price,
        requires_prescription=requires_prescription,
    )
    variant = ProductVariant.objects.create(
        product=product, sku=f"{sku}-DEF", price=Decimal(str(price)), stock_quantity=50,
    )
    return product, variant


class RxCheckoutTestBase(TestCase):
    def setUp(self):
        # Same rationale as storefront/test_shipping_fee_checkout.py: the
        # checkout endpoint is throttled and the counter is process-wide.
        cache.clear()
        self.client = APIClient()
        self.cat = Categories.objects.create(name="Pharmacy", slug="rx-pharmacy", description="")

    def place_order(self, items):
        payload = {
            "items": items,
            "shipping_address": {"address": "1 Test Rd", "city": "Dhaka"},
            "contact_name": "Karim", "contact_phone": "01711112222",
        }
        return self.client.post("/api/store/orders/", payload, format="json")


class RxBlockedWhileSwitchOffTests(RxCheckoutTestBase):
    def test_rx_product_cannot_be_checked_out_while_disabled(self):
        cfg = StoreConfiguration.get_solo()
        self.assertFalse(cfg.rx_sales_enabled)  # confirms the documented default

        product, variant = make_product(
            "Napa Extra", "rx-napa", "RX-NAPA", 50, self.cat, requires_prescription=True)

        res = self.place_order([{"variant_id": variant.id, "quantity": 1}])
        self.assertEqual(res.status_code, 400, res.content)
        self.assertEqual(Order.objects.count(), 0)


class RxAllowedWhileSwitchOnTests(RxCheckoutTestBase):
    def test_rx_product_can_be_checked_out_once_enabled(self):
        cfg = StoreConfiguration.get_solo()
        cfg.rx_sales_enabled = True
        cfg.save()

        product, variant = make_product(
            "Seclo 20", "rx-seclo", "RX-SECLO", 80, self.cat, requires_prescription=True)

        res = self.place_order([{"variant_id": variant.id, "quantity": 1}])
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(Order.objects.count(), 1)


class NonRxProductUnaffectedTests(RxCheckoutTestBase):
    def test_non_rx_product_checks_out_regardless_of_switch(self):
        cfg = StoreConfiguration.get_solo()
        self.assertFalse(cfg.rx_sales_enabled)

        product, variant = make_product(
            "Vitamin C", "rx-vitc", "RX-VITC", 200, self.cat, requires_prescription=False)

        res = self.place_order([{"variant_id": variant.id, "quantity": 1}])
        self.assertEqual(res.status_code, 201, res.content)

    def test_mixed_cart_blocked_by_the_rx_line_even_if_other_line_is_plain(self):
        # One Rx line in an otherwise-plain cart must still block the whole
        # order -- place_cod_order is one atomic transaction, so a partial
        # checkout that drops the Rx line silently is not an option either.
        cfg = StoreConfiguration.get_solo()
        self.assertFalse(cfg.rx_sales_enabled)

        plain, plain_v = make_product("Shampoo", "rx-shampoo", "RX-SHAMPOO", 300, self.cat)
        rx, rx_v = make_product(
            "Losectil", "rx-losectil", "RX-LOSECTIL", 60, self.cat, requires_prescription=True)

        res = self.place_order([
            {"variant_id": plain_v.id, "quantity": 1},
            {"variant_id": rx_v.id, "quantity": 1},
        ])
        self.assertEqual(res.status_code, 400, res.content)
        self.assertEqual(Order.objects.count(), 0)
