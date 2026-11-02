"""A placed food order must reach the owner's inbox.

Store orders have alerted by email since orders/services.py was wired, but
place_food_cod_order only ever called notify() — which creates an in-app
Notification and an Expo push for the CUSTOMER. Nothing told the owner a food
order had arrived, so an order could sit unconfirmed until someone happened to
open the admin panel. On a delivery business that is the order going cold.
"""
from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase

from core.models import StoreConfiguration
from food.models import DeliveryZone, FoodCategory, FoodItem, Restaurant, RestaurantHours
from food.services import place_food_cod_order


class FoodOrderAdminEmailTests(TestCase):
    def setUp(self):
        cache.clear()
        cfg = StoreConfiguration.get_solo()
        cfg.alert_email = "owner@fabrything.com"
        cfg.save()

        self.zone = DeliveryZone.objects.create(name="Sadar", center_lat="23.8", center_lng="90.4", radius_km="5", is_active=True)
        self.restaurant = Restaurant.objects.create(
            name="Rahim Hotel", slug="rahim", status=Restaurant.Status.ACTIVE,
            is_open=True, is_accepting_orders=True, min_order_amount=Decimal("0.00"),
        )
        # is_currently_open() is hours-driven; with no rows the restaurant is
        # closed and checkout refuses the order.
        for weekday in range(7):
            RestaurantHours.objects.create(
                restaurant=self.restaurant, weekday=weekday,
                open_time="00:00", close_time="23:59",
            )
        category = FoodCategory.objects.create(restaurant=self.restaurant, name="Mains")
        self.item = FoodItem.objects.create(
            restaurant=self.restaurant, category_id=category, name="Biryani",
            price=Decimal("180.00"), is_available=True,
        )

    def _place(self):
        return place_food_cod_order(
            customer=None, restaurant_slug="rahim",
            items=[{"item_id": self.item.id, "quantity": 2}],
            contact_name="Billal", contact_phone="8801842168117",
            delivery_address="Ujanchar bazar", zone_id=self.zone.id,
        )

    @patch("food.services.send_email_alert_on_commit")
    def test_owner_is_emailed_when_a_food_order_is_placed(self, mailer):
        with self.captureOnCommitCallbacks(execute=True):
            order = self._place()

        self.assertTrue(mailer.called, "no admin email was sent for a food order")
        to, kwargs = mailer.call_args[0][0], mailer.call_args[1]
        self.assertEqual(to, "owner@fabrything.com")
        self.assertEqual(kwargs["related_order"], order.order_code)
        self.assertIn(order.order_code, kwargs["subject"])

    @patch("food.services.send_email_alert_on_commit")
    def test_the_email_carries_what_the_owner_needs_to_act(self, mailer):
        with self.captureOnCommitCallbacks(execute=True):
            order = self._place()
        body = mailer.call_args[1]["body"]
        # Enough to ring the customer and start the kitchen without opening
        # the panel first.
        self.assertIn("Billal", body)
        self.assertIn("8801842168117", body)
        self.assertIn("Ujanchar bazar", body)
        self.assertIn("Rahim Hotel", body)
        self.assertIn(str(order.total), body)

    @patch("food.services.send_email_alert_on_commit")
    def test_a_blank_alert_email_is_not_an_error(self, mailer):
        cache.clear()
        cfg = StoreConfiguration.get_solo()
        cfg.alert_email = ""
        cfg.save()
        with self.captureOnCommitCallbacks(execute=True):
            self._place()
        # send_email_alert no-ops on a blank address; the order must still be
        # placed rather than the alert taking checkout down with it.
        self.assertEqual(mailer.call_args[0][0], "")

    def test_a_dead_mail_server_never_loses_the_order(self):
        """The realistic failure: SMTP is down when the alert actually sends.

        The alert runs in an on_commit callback, so it fires AFTER the order is
        committed, and send_email_alert swallows every exception by design.
        Patching the wrapper to raise (an earlier version of this test) tested
        a path that cannot occur — the wrapper only schedules a callback.
        """
        from food.models import FoodOrder

        with patch("core.email_alerts.send_mail", side_effect=RuntimeError("smtp down")):
            with self.captureOnCommitCallbacks(execute=True):
                order = self._place()

        # Order stands; only the alert was lost.
        self.assertTrue(FoodOrder.objects.filter(pk=order.pk).exists())

    def test_the_alert_is_deferred_until_after_commit(self):
        """Sending inline would hold the select_for_update locks this function
        takes for the length of an SMTP handshake, serialising checkout."""
        sent = []
        with patch("core.email_alerts.send_mail", side_effect=lambda **kw: sent.append(kw)):
            with self.captureOnCommitCallbacks(execute=False):
                self._place()
            # Nothing sent while the transaction was still open.
            self.assertEqual(sent, [])
