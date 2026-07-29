"""Store order placement -> WhatsApp alert to the admin (core.whatsapp).

Dormant by default (no env credentials in test settings); these tests patch
the env + the HTTP call to exercise the wired-but-inert integration without
ever touching the network. See core/test_whatsapp.py for the provider unit
tests themselves — these are the storefront integration point.
"""
from decimal import Decimal
from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Categories, Products, ProductVariant
from core.models import StoreConfiguration, WhatsAppAlertLog
from orders.models import Order

ENV_CONFIGURED = {
    "WHATSAPP_ACCESS_TOKEN": "tok",
    "WHATSAPP_PHONE_NUMBER_ID": "123",
}


class PlaceOrderWhatsAppAlertTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Categories.objects.create(name="Tees", slug="tees", description="d")
        self.product = Products.objects.create(
            name="Tee", slug="tee", description="d", sku="SKU-1",
            initial_buying_price=100, initial_selling_price=200,
            category_id=self.category, status="ACTIVE",
        )
        self.variant = ProductVariant.objects.create(
            product=self.product, sku="SKU-1-M", size="M", price=Decimal("200.00"),
            stock_quantity=10,
        )
        config = StoreConfiguration.get_solo()
        config.whatsapp_admin_number = "8801700000001"
        config.save()

    def _place_order(self):
        payload = {
            "items": [{"variant_id": self.variant.id, "quantity": 2}],
            "contact_name": "Karim Uddin",
            "contact_phone": "01700000002",
            "shipping_address": {"address": "123 Road", "city": "Dhaka"},
        }
        return self.client.post("/api/store/orders/", payload, format="json")

    @mock.patch("core.whatsapp.requests.post")
    @mock.patch.dict("os.environ", ENV_CONFIGURED, clear=True)
    def test_placing_an_order_triggers_exactly_one_admin_alert_after_commit(self, mock_post):
        mock_post.return_value = mock.Mock(ok=True, status_code=200, text="")

        with self.captureOnCommitCallbacks(execute=True):
            res = self._place_order()

        self.assertEqual(res.status_code, 201, res.content)
        order_number = res.json()["data"]["order_number"]

        alerts = WhatsAppAlertLog.objects.filter(kind="store_order_admin")
        self.assertEqual(alerts.count(), 1)
        alert = alerts.get()
        self.assertEqual(alert.recipient, "8801700000001")
        self.assertEqual(alert.related_order, order_number)
        self.assertTrue(alert.success)
        mock_post.assert_called_once()

    @mock.patch("core.whatsapp.requests.post")
    @mock.patch.dict("os.environ", {}, clear=True)
    def test_unconfigured_provider_still_places_the_order_and_sends_nothing(self, mock_post):
        with self.captureOnCommitCallbacks(execute=True):
            res = self._place_order()

        self.assertEqual(res.status_code, 201, res.content)
        self.assertTrue(Order.objects.filter(order_number=res.json()["data"]["order_number"]).exists())
        mock_post.assert_not_called()
        self.assertEqual(WhatsAppAlertLog.objects.count(), 0)

    @mock.patch("core.whatsapp.requests.post", side_effect=TimeoutError("no route to host"))
    @mock.patch.dict("os.environ", ENV_CONFIGURED, clear=True)
    def test_whatsapp_failure_does_not_fail_order_placement(self, mock_post):
        with self.captureOnCommitCallbacks(execute=True):
            res = self._place_order()

        # The order still exists and the endpoint still reports success — an
        # alert failing must never roll back or block an order.
        self.assertEqual(res.status_code, 201, res.content)
        order_number = res.json()["data"]["order_number"]
        self.assertTrue(Order.objects.filter(order_number=order_number).exists())

        alert = WhatsAppAlertLog.objects.get(kind="store_order_admin")
        self.assertFalse(alert.success)
        self.assertIn("no route to host", alert.error)

    @mock.patch("core.whatsapp.requests.post")
    @mock.patch.dict("os.environ", ENV_CONFIGURED, clear=True)
    def test_no_admin_number_configured_sends_nothing(self, mock_post):
        config = StoreConfiguration.get_solo()
        config.whatsapp_admin_number = ""
        config.save()

        with self.captureOnCommitCallbacks(execute=True):
            res = self._place_order()

        self.assertEqual(res.status_code, 201, res.content)
        mock_post.assert_not_called()
        self.assertEqual(WhatsAppAlertLog.objects.count(), 0)
