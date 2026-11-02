"""Rider cash: the platform's money sitting in a rider's pocket."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from food.models import (DeliveryPricing, FoodOrder, OrderSettlement, Restaurant, Rider,
                         RiderCashDeposit)
from food.services_cash import (cash_in_hand, collected_total, deposited_total, over_ceiling,
                                record_deposit)
from food.services_dispatch import pick_rider_for
from food.services_settlement import settle_order

User = get_user_model()


def delivered_order(rider, total="500.00", method="COD", restaurant=None):
    restaurant = restaurant or Restaurant.objects.create(
        name="R", slug=f"r{Restaurant.objects.count()}")
    order = FoodOrder.objects.create(
        guest_name="A", guest_phone="017", delivery_address="x", restaurant=restaurant,
        rider=rider, subtotal=Decimal(total), delivery_fee=Decimal("0.00"),
        total=Decimal(total), payment_method=method, status=FoodOrder.Status.DELIVERED)
    settle_order(order)
    return order


class CashInHandTests(TestCase):
    def setUp(self):
        self.rider = Rider.objects.create(name="Karim")

    def test_a_new_rider_holds_nothing(self):
        self.assertEqual(cash_in_hand(self.rider), Decimal("0.00"))

    def test_a_delivered_cod_order_puts_cash_in_the_riders_pocket(self):
        delivered_order(self.rider, "500.00")
        self.assertEqual(cash_in_hand(self.rider), Decimal("500.00"))

    def test_a_prepaid_order_puts_no_cash_anywhere(self):
        """There is nothing to collect on an order already paid online, so it
        must not count against the rider's limit."""
        delivered_order(self.rider, "500.00", method="BKASH")
        self.assertEqual(cash_in_hand(self.rider), Decimal("0.00"))

    def test_depositing_clears_the_balance(self):
        delivered_order(self.rider, "500.00")
        record_deposit(self.rider, "500.00")
        self.assertEqual(cash_in_hand(self.rider), Decimal("0.00"))

    def test_a_partial_deposit_leaves_the_rest_outstanding(self):
        delivered_order(self.rider, "500.00")
        delivered_order(self.rider, "300.00")
        record_deposit(self.rider, "500.00")
        self.assertEqual(cash_in_hand(self.rider), Decimal("300.00"))

    def test_an_over_deposit_is_a_credit_not_a_negative_debt(self):
        delivered_order(self.rider, "480.00")
        record_deposit(self.rider, "500.00")   # rider handed over a round number
        self.assertEqual(cash_in_hand(self.rider), Decimal("0.00"))

    def test_the_balance_is_derived_so_it_cannot_drift_from_the_ledger(self):
        """No stored counter to go stale: delete the deposit row and the debt
        reappears, because the number is computed from collections minus
        deposits every time it is asked for."""
        delivered_order(self.rider, "500.00")
        record_deposit(self.rider, "500.00")
        RiderCashDeposit.objects.all().delete()
        self.assertEqual(cash_in_hand(self.rider), Decimal("500.00"))

    def test_collections_and_deposits_are_reported_separately(self):
        delivered_order(self.rider, "500.00")
        record_deposit(self.rider, "200.00")
        self.assertEqual(collected_total(self.rider), Decimal("500.00"))
        self.assertEqual(deposited_total(self.rider), Decimal("200.00"))

    def test_a_deposit_settles_the_oldest_leg_first(self):
        first = delivered_order(self.rider, "300.00")
        second = delivered_order(self.rider, "400.00")
        record_deposit(self.rider, "300.00")
        self.assertEqual(OrderSettlement.objects.get(order=first).rider_cash_status, "SETTLED")
        self.assertEqual(OrderSettlement.objects.get(order=second).rider_cash_status, "PENDING")

    def test_a_deposit_too_small_to_cover_a_leg_settles_nothing(self):
        order = delivered_order(self.rider, "500.00")
        record_deposit(self.rider, "100.00")
        # Marking a partly-covered leg settled would overstate what came back.
        self.assertEqual(OrderSettlement.objects.get(order=order).rider_cash_status, "PENDING")
        self.assertEqual(cash_in_hand(self.rider), Decimal("400.00"))

    def test_a_zero_or_negative_deposit_is_refused(self):
        for bad in ["0", "-50"]:
            with self.assertRaises(ValueError):
                record_deposit(self.rider, bad)


class CashCeilingTests(TestCase):
    """The ceiling is the actual protection; the reporting is just visibility."""

    def setUp(self):
        self.cfg = DeliveryPricing.get_solo()
        self.cfg.rider_cash_ceiling = Decimal("1000.00")
        self.cfg.save()
        self.rider = Rider.objects.create(
            name="Karim", is_available=True, last_seen_at=timezone.now(),
            current_lat=Decimal("23.77"), current_lng=Decimal("90.78"))
        self.restaurant = Restaurant.objects.create(name="R", slug="r",
                                                    pickup_lat=Decimal("23.77"),
                                                    pickup_lng=Decimal("90.78"))

    def _pending_order(self, method="COD"):
        return FoodOrder.objects.create(
            guest_name="A", guest_phone="017", delivery_address="x",
            restaurant=self.restaurant, subtotal=Decimal("200.00"), total=Decimal("200.00"),
            payment_method=method, status=FoodOrder.Status.CONFIRMED)

    def test_a_rider_under_the_limit_is_dispatchable(self):
        delivered_order(self.rider, "500.00", restaurant=self.restaurant)
        self.assertFalse(over_ceiling(self.rider))
        self.assertEqual(pick_rider_for(self._pending_order()), self.rider)

    def test_a_rider_over_the_limit_stops_getting_cash_orders(self):
        delivered_order(self.rider, "1200.00", restaurant=self.restaurant)
        self.assertTrue(over_ceiling(self.rider))
        self.assertIsNone(pick_rider_for(self._pending_order()))

    def test_they_still_get_prepaid_orders(self):
        """The ceiling bounds cash exposure, it does not stop someone working."""
        delivered_order(self.rider, "1200.00", restaurant=self.restaurant)
        self.assertEqual(pick_rider_for(self._pending_order(method="BKASH")), self.rider)

    def test_depositing_puts_them_back_in_the_pool(self):
        delivered_order(self.rider, "1200.00", restaurant=self.restaurant)
        record_deposit(self.rider, "1200.00")
        self.assertEqual(pick_rider_for(self._pending_order()), self.rider)

    def test_a_nearer_rider_over_the_limit_yields_to_a_further_one(self):
        far = Rider.objects.create(name="Far", is_available=True, last_seen_at=timezone.now(),
                                   current_lat=Decimal("23.85"), current_lng=Decimal("90.78"))
        delivered_order(self.rider, "1200.00", restaurant=self.restaurant)
        self.assertEqual(pick_rider_for(self._pending_order()), far)


class AdminCashApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(username="boss", email="b@e.com",
                                              password="x", role="Admin")
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.admin).access_token}")
        self.rider = Rider.objects.create(name="Karim")
        delivered_order(self.rider, "500.00")

    def test_the_list_answers_who_owes_us_money(self):
        d = self.client.get("/api/food/admin/rider-cash/").json()["data"]
        self.assertEqual(d["riders"][0]["cash_in_hand"], "500.00")
        self.assertEqual(d["total_outstanding"], "500.00")

    def test_recording_a_deposit_updates_the_balance(self):
        res = self.client.post(f"/api/food/admin/rider-cash/{self.rider.id}/deposit/",
                               {"amount": "500.00", "note": "evening handover"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["data"]["cash_in_hand"], "0.00")

    def test_the_deposit_records_who_received_it(self):
        self.client.post(f"/api/food/admin/rider-cash/{self.rider.id}/deposit/",
                         {"amount": "500.00"}, format="json")
        self.assertEqual(RiderCashDeposit.objects.get().received_by, self.admin)

    def test_a_bad_amount_is_a_400_not_a_500(self):
        res = self.client.post(f"/api/food/admin/rider-cash/{self.rider.id}/deposit/",
                               {"amount": "-5"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_cash_records_are_admin_only(self):
        self.client.credentials()
        self.assertIn(self.client.get("/api/food/admin/rider-cash/").status_code, (401, 403))
