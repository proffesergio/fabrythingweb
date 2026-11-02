"""Food dispatch -> WhatsApp alerts (core.whatsapp).

A rider offer created by services_dispatch.offer_order alerts that rider on
WhatsApp; an order that falls through with no rider available alerts the
admin instead. Dormant by default — these tests patch the env + the HTTP
call, never the network.
"""
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from core.models import StoreConfiguration, WhatsAppAlertLog
from food.models import Restaurant, Rider, FoodOrder, DeliveryOffer
from food.services_dispatch import maybe_auto_assign_rider, offer_order

User = get_user_model()

BANCHARAMPUR = (Decimal("23.7104"), Decimal("90.9280"))

ENV_CONFIGURED = {
    "WHATSAPP_ACCESS_TOKEN": "tok",
    "WHATSAPP_PHONE_NUMBER_ID": "123",
}


def make_rider(name, *, lat=None, lng=None, seen_minutes_ago=0, available=True, phone=""):
    user = User.objects.create(username=f"u_{name}", email=f"{name}@x.com", role="Rider")
    return Rider.objects.create(
        user=user, name=name, is_available=available, phone=phone,
        current_lat=lat, current_lng=lng,
        last_seen_at=timezone.now() - timedelta(minutes=seen_minutes_ago),
    )


class RiderOfferWhatsAppTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(
            name="Test Kitchen", slug="test-kitchen", status=Restaurant.Status.ACTIVE,
            pickup_lat=BANCHARAMPUR[0], pickup_lng=BANCHARAMPUR[1],
        )
        self.order = FoodOrder.objects.create(
            guest_name="G", guest_phone="017", delivery_address="42 Lake Road",
            restaurant=self.restaurant, subtotal=Decimal("300"), total=Decimal("330"),
            rider_base_pay=Decimal("45.00"), status=FoodOrder.Status.CONFIRMED,
        )

    @mock.patch("core.whatsapp.requests.post")
    @mock.patch.dict("os.environ", ENV_CONFIGURED, clear=True)
    def test_offering_the_order_alerts_the_rider_on_whatsapp(self, mock_post):
        mock_post.return_value = mock.Mock(ok=True, status_code=200, text="")
        rider = make_rider("r1", lat=BANCHARAMPUR[0], lng=BANCHARAMPUR[1],
                           seen_minutes_ago=1, phone="8801711111111")

        with self.captureOnCommitCallbacks(execute=True):
            offer = maybe_auto_assign_rider(self.order)

        self.assertIsNotNone(offer)
        self.assertEqual(offer.rider, rider)

        alert = WhatsAppAlertLog.objects.get(kind="food_rider_offer")
        self.assertEqual(alert.recipient, "8801711111111")
        self.assertEqual(alert.related_order, self.order.order_code)
        self.assertTrue(alert.success)
        self.assertIn("Test Kitchen", alert.payload_summary)
        self.assertIn("45.00", alert.payload_summary)

    @mock.patch("core.whatsapp.requests.post")
    @mock.patch.dict("os.environ", {}, clear=True)
    def test_unconfigured_provider_still_creates_the_offer(self, mock_post):
        make_rider("r1", lat=BANCHARAMPUR[0], lng=BANCHARAMPUR[1],
                  seen_minutes_ago=1, phone="8801711111111")

        with self.captureOnCommitCallbacks(execute=True):
            offer = maybe_auto_assign_rider(self.order)

        self.assertIsNotNone(offer)
        mock_post.assert_not_called()
        self.assertEqual(WhatsAppAlertLog.objects.count(), 0)

    @mock.patch("core.whatsapp.requests.post")
    @mock.patch.dict("os.environ", ENV_CONFIGURED, clear=True)
    def test_rider_with_no_phone_number_sends_nothing(self, mock_post):
        make_rider("r1", lat=BANCHARAMPUR[0], lng=BANCHARAMPUR[1], seen_minutes_ago=1, phone="")

        with self.captureOnCommitCallbacks(execute=True):
            offer = maybe_auto_assign_rider(self.order)

        self.assertIsNotNone(offer)
        mock_post.assert_not_called()
        self.assertEqual(WhatsAppAlertLog.objects.filter(kind="food_rider_offer").count(), 0)


class NoRiderAvailableWhatsAppTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(
            name="Lonely Kitchen", slug="lonely-kitchen", status=Restaurant.Status.ACTIVE,
            pickup_lat=BANCHARAMPUR[0], pickup_lng=BANCHARAMPUR[1],
        )
        self.order = FoodOrder.objects.create(
            guest_name="G", guest_phone="017", delivery_address="42 Lake Road",
            restaurant=self.restaurant, subtotal=Decimal("300"), total=Decimal("330"),
            status=FoodOrder.Status.CONFIRMED,
        )
        config = StoreConfiguration.get_solo()
        config.whatsapp_admin_number = "8801700000009"
        config.save()

    @mock.patch("core.whatsapp.requests.post")
    @mock.patch.dict("os.environ", ENV_CONFIGURED, clear=True)
    def test_no_rider_available_alerts_the_admin(self, mock_post):
        mock_post.return_value = mock.Mock(ok=True, status_code=200, text="")

        with self.captureOnCommitCallbacks(execute=True):
            result = offer_order(self.order)

        self.assertIsNone(result)
        alert = WhatsAppAlertLog.objects.get(kind="food_no_rider_admin")
        self.assertEqual(alert.recipient, "8801700000009")
        self.assertEqual(alert.related_order, self.order.order_code)
        self.assertTrue(alert.success)
        self.assertIn("Lonely Kitchen", alert.payload_summary)

    @mock.patch("core.whatsapp.requests.post")
    @mock.patch.dict("os.environ", ENV_CONFIGURED, clear=True)
    def test_does_not_spam_the_admin_on_repeated_sweeps(self, mock_post):
        mock_post.return_value = mock.Mock(ok=True, status_code=200, text="")

        with self.captureOnCommitCallbacks(execute=True):
            offer_order(self.order)
        with self.captureOnCommitCallbacks(execute=True):
            offer_order(self.order)
        with self.captureOnCommitCallbacks(execute=True):
            offer_order(self.order)

        self.assertEqual(WhatsAppAlertLog.objects.filter(kind="food_no_rider_admin").count(), 1)
        mock_post.assert_called_once()
