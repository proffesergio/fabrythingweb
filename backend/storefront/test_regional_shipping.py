from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Categories, Products, ProductVariant
from core.models import INSIDE_DHAKA, OUTSIDE_DHAKA, StoreConfiguration
from orders.models import Order


class RegionalShippingCheckoutTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        category = Categories.objects.create(name="Shipping", slug="shipping", description="")
        product = Products.objects.create(
            name="Regional item", slug="regional-item", sku="REGIONAL",
            category_id=category, status="ACTIVE", description="",
            initial_buying_price=Decimal("200"), initial_selling_price=Decimal("200"),
        )
        self.variant = ProductVariant.objects.create(
            product=product, sku="REGIONAL-1", price=Decimal("200"), stock_quantity=10,
        )
        self.cfg = StoreConfiguration.get_solo()
        self.cfg.fixed_shipping_rate = Decimal("70")
        self.cfg.outside_dhaka_shipping_rate = Decimal("120")
        self.cfg.free_shipping_threshold = None
        self.cfg.save()

    def checkout(self, zone, city="Dhaka", district=""):
        payload = {
            "items": [{"variant_id": self.variant.id, "quantity": 1}],
            "shipping_address": {"address": "1 Test Road", "city": city, "state": district},
            "contact_name": "Karim", "contact_phone": "01711112222",
        }
        if zone is not None:
            payload["delivery_zone"] = zone
        return self.client.post("/api/store/orders/", payload, format="json")

    def test_public_config_exposes_both_rates(self):
        response = self.client.get("/api/store/config/")
        self.assertEqual(response.json()["data"]["fixed_shipping_rate"], 70.0)
        self.assertEqual(response.json()["data"]["outside_dhaka_shipping_rate"], 120.0)

    def test_inside_dhaka_rate_and_zone_are_stored(self):
        response = self.checkout(INSIDE_DHAKA)
        self.assertEqual(response.status_code, 201, response.content)
        order = Order.objects.get(order_number=response.json()["data"]["order_number"])
        self.assertEqual(order.shipping_amount, Decimal("70"))
        self.assertEqual(order.shipping_address["delivery_zone"], INSIDE_DHAKA)

    def test_outside_dhaka_rate_and_zone_are_stored(self):
        response = self.checkout(OUTSIDE_DHAKA, city="Sylhet", district="Sylhet")
        self.assertEqual(response.status_code, 201, response.content)
        order = Order.objects.get(order_number=response.json()["data"]["order_number"])
        self.assertEqual(order.shipping_amount, Decimal("120"))
        self.assertEqual(order.shipping_address["delivery_zone"], OUTSIDE_DHAKA)

    def test_inside_zone_rejects_conflicting_district(self):
        response = self.checkout(INSIDE_DHAKA, city="Dhaka", district="Sylhet")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Order.objects.exists())

    def test_inside_zone_accepts_bangla_dhaka(self):
        response = self.checkout(INSIDE_DHAKA, city=" ঢাকা ", district="ঢাকা")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["data"]["shipping_amount"], 70.0)

    def test_inside_zone_accepts_dhaka_neighborhood(self):
        response = self.checkout(INSIDE_DHAKA, city="Dhanmondi", district="Dhaka")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["data"]["shipping_amount"], 70.0)

    def test_inside_zone_rejects_outside_city_even_with_dhaka_district(self):
        response = self.checkout(INSIDE_DHAKA, city="Sylhet", district="Dhaka")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Order.objects.exists())

    def test_invalid_zone_is_rejected(self):
        response = self.checkout("somewhere_else")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Order.objects.exists())

    def test_legacy_address_outside_dhaka_uses_outside_rate(self):
        response = self.checkout(None, city="Sylhet", district="Sylhet")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["data"]["shipping_amount"], 120.0)

    def test_outside_product_override_and_free_threshold(self):
        self.variant.product.shipping_fee = Decimal("250")
        self.variant.product.save()
        response = self.checkout(OUTSIDE_DHAKA, city="Sylhet")
        self.assertEqual(response.json()["data"]["shipping_amount"], 250.0)
        self.cfg.free_shipping_threshold = Decimal("200")
        self.cfg.save()
        response = self.checkout(OUTSIDE_DHAKA, city="Sylhet")
        self.assertEqual(response.json()["data"]["shipping_amount"], 0.0)
