"""Store order placement -> email alert to the owner (core.email_alerts).

Unlike the WhatsApp alerts next door, this channel is LIVE: it needs no env
credentials to be considered "on", only SMTP settings to actually leave the
box. So the integration contract under test is the one the business depends
on — every accepted order produces exactly one alert, addressed to the mailbox
configured in StoreConfiguration, and no email failure can cost an order.
"""
from decimal import Decimal
from unittest import mock

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from catalog.models import Categories, Products, ProductVariant
from core.models import StoreConfiguration
from orders.models import Order


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PlaceOrderEmailAlertTests(TestCase):
    def setUp(self):
        # POST /api/store/orders/ is throttled and ScopedRateThrottle counts in
        # the process-wide cache — same reason test_whatsapp_alerts.py clears it.
        cache.clear()
        mail.outbox = []
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
        config.alert_email = "owner@fabrything.com"
        config.save()

    def _place_order(self):
        return self.client.post("/api/store/orders/", {
            "items": [{"variant_id": self.variant.id, "quantity": 2}],
            "contact_name": "Karim Uddin",
            "contact_phone": "01700000002",
            "shipping_address": {"address": "123 Road", "city": "Dhaka"},
        }, format="json")

    def test_placing_an_order_emails_the_owner_once_after_commit(self):
        with self.captureOnCommitCallbacks(execute=True):
            res = self._place_order()

        self.assertEqual(res.status_code, 201, res.content)
        order_number = res.json()["data"]["order_number"]

        self.assertEqual(len(mail.outbox), 1)
        alert = mail.outbox[0]
        self.assertEqual(alert.to, ["owner@fabrything.com"])
        self.assertIn(order_number, alert.subject)
        # The owner must be able to act on the alert without opening the panel:
        # who ordered, how to reach them, and what it is worth.
        self.assertIn("Karim Uddin", alert.body)
        self.assertIn("01700000002", alert.body)
        self.assertIn(order_number, alert.body)

    def test_alert_is_not_sent_before_the_transaction_commits(self):
        """An order that rolls back must not have emailed the owner about it."""
        with self.captureOnCommitCallbacks(execute=False):
            self._place_order()
        self.assertEqual(len(mail.outbox), 0)

    def test_blank_alert_email_disables_the_channel_without_breaking_checkout(self):
        config = StoreConfiguration.get_solo()
        config.alert_email = ""
        config.save()

        with self.captureOnCommitCallbacks(execute=True):
            res = self._place_order()

        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(len(mail.outbox), 0)

    def test_smtp_failure_does_not_fail_order_placement(self):
        """The money rule: a refused mail server costs an alert, never a sale."""
        with mock.patch("core.email_alerts.send_mail",
                        side_effect=OSError("connection refused")):
            with self.captureOnCommitCallbacks(execute=True):
                res = self._place_order()

        self.assertEqual(res.status_code, 201, res.content)
        self.assertTrue(
            Order.objects.filter(order_number=res.json()["data"]["order_number"]).exists())
