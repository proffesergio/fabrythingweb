from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from food.models import FoodOrder, OrderSettlement, Restaurant, Rider
from food.services_settlement import (
    backfill_settlements, compute_breakdown, settle_leg, settle_order,
)

User = get_user_model()


def make_order(**kwargs):
    restaurant = kwargs.pop("restaurant", None) or Restaurant.objects.create(
        name="Test Co", slug=f"test-co-{Restaurant.objects.count()}",
        commission_percentage=Decimal("15.00"))
    defaults = dict(
        guest_name="A", guest_phone="017", delivery_address="somewhere",
        restaurant=restaurant, subtotal=Decimal("500.00"), discount=Decimal("0.00"),
        delivery_fee=Decimal("50.00"), tip=Decimal("20.00"), total=Decimal("570.00"),
    )
    defaults.update(kwargs)
    return FoodOrder.objects.create(**defaults)


class BreakdownTests(TestCase):
    def setUp(self):
        self.rider = Rider.objects.create(name="Karim")

    def test_splits_add_up_to_the_order_total(self):
        order = make_order(rider=self.rider)
        b = compute_breakdown(order)

        # 500 food, 15% commission -> 75 platform / 425 restaurant.
        self.assertEqual(b["food_net"], Decimal("500.00"))
        self.assertEqual(b["commission_amount"], Decimal("75.00"))
        self.assertEqual(b["restaurant_payout"], Decimal("425.00"))
        # Rider: 40 flat + the 20 tip.
        self.assertEqual(b["rider_base_pay"], Decimal("40.00"))
        self.assertEqual(b["rider_payout"], Decimal("60.00"))
        # Platform keeps commission + delivery fee - what it pays the rider.
        self.assertEqual(b["platform_revenue"], Decimal("85.00"))

        # The books must balance against the amount the customer actually paid.
        self.assertEqual(
            b["restaurant_payout"] + b["commission_amount"] + b["delivery_fee"] + b["tip"],
            order.total)
        # And every taka is accounted for across the three parties.
        self.assertEqual(
            b["restaurant_payout"] + b["rider_payout"] + b["platform_revenue"],
            order.total)

    def test_discount_comes_off_before_commission(self):
        order = make_order(rider=self.rider, subtotal=Decimal("500.00"),
                           discount=Decimal("100.00"), total=Decimal("470.00"))
        b = compute_breakdown(order)
        self.assertEqual(b["food_net"], Decimal("400.00"))
        self.assertEqual(b["commission_amount"], Decimal("60.00"))
        self.assertEqual(b["restaurant_payout"], Decimal("340.00"))

    def test_order_without_rider_pays_no_base_pay(self):
        order = make_order(rider=None)
        b = compute_breakdown(order)
        self.assertEqual(b["rider_base_pay"], Decimal("0.00"))
        self.assertEqual(b["rider_payout"], Decimal("20.00"))  # tip only
        self.assertEqual(b["platform_revenue"], Decimal("125.00"))  # 75 + 50 - 0


class SettleOrderTests(TestCase):
    def setUp(self):
        self.rider = Rider.objects.create(name="Karim")

    def test_creates_settlement_with_snapshotted_rate(self):
        order = make_order(rider=self.rider)
        s = settle_order(order)
        self.assertEqual(s.commission_rate, Decimal("15.00"))
        self.assertEqual(s.rider_name, "Karim")
        self.assertEqual(s.restaurant_payout, Decimal("425.00"))

        # Changing the restaurant's rate later must not move the settled books.
        order.restaurant.commission_percentage = Decimal("30.00")
        order.restaurant.save()
        s.refresh_from_db()
        self.assertEqual(s.commission_rate, Decimal("15.00"))
        self.assertEqual(s.restaurant_payout, Decimal("425.00"))

    def test_is_idempotent(self):
        order = make_order(rider=self.rider)
        first = settle_order(order)
        second = settle_order(order)
        self.assertEqual(first.id, second.id)
        self.assertEqual(OrderSettlement.objects.filter(order=order).count(), 1)

    def test_cod_order_starts_with_pending_cash_legs(self):
        order = make_order(rider=self.rider, payment_method="COD")
        s = settle_order(order)
        self.assertEqual(s.customer_payment_status, OrderSettlement.Settle.PENDING)
        self.assertEqual(s.rider_cash_status, OrderSettlement.Settle.PENDING)

    def test_prepaid_order_needs_no_cash_collection(self):
        order = make_order(rider=self.rider, payment_method="BKASH")
        s = settle_order(order)
        self.assertEqual(s.customer_payment_status, OrderSettlement.Settle.SETTLED)
        self.assertEqual(s.rider_cash_status, OrderSettlement.Settle.NA)

    def test_order_without_rider_has_na_rider_legs(self):
        order = make_order(rider=None)
        s = settle_order(order)
        self.assertEqual(s.rider_payout_status, OrderSettlement.Settle.NA)
        self.assertEqual(s.rider_cash_status, OrderSettlement.Settle.NA)


class SettleLegTests(TestCase):
    def setUp(self):
        self.rider = Rider.objects.create(name="Karim")
        self.settlement = settle_order(make_order(rider=self.rider))

    def test_marking_a_leg_settled_stamps_the_time(self):
        settle_leg(self.settlement, "rider_payout")
        self.settlement.refresh_from_db()
        self.assertEqual(self.settlement.rider_payout_status, OrderSettlement.Settle.SETTLED)
        self.assertIsNotNone(self.settlement.rider_payout_at)

    def test_a_leg_can_be_reverted(self):
        settle_leg(self.settlement, "rider_payout")
        settle_leg(self.settlement, "rider_payout", settled=False)
        self.settlement.refresh_from_db()
        self.assertEqual(self.settlement.rider_payout_status, OrderSettlement.Settle.PENDING)
        self.assertIsNone(self.settlement.rider_payout_at)

    def test_customer_payment_syncs_the_order_flag(self):
        settle_leg(self.settlement, "customer_payment")
        self.settlement.order.refresh_from_db()
        self.assertEqual(self.settlement.order.payment_status, "COLLECTED")

    def test_na_leg_cannot_be_settled(self):
        s = settle_order(make_order(rider=None))
        settle_leg(s, "rider_payout")
        s.refresh_from_db()
        self.assertEqual(s.rider_payout_status, OrderSettlement.Settle.NA)

    def test_unknown_leg_raises(self):
        with self.assertRaises(ValueError):
            settle_leg(self.settlement, "not_a_leg")

    def test_fully_settled_when_every_leg_is_done_or_na(self):
        self.assertFalse(self.settlement.is_fully_settled)
        for leg in OrderSettlement.LEGS:
            settle_leg(self.settlement, leg)
        self.settlement.refresh_from_db()
        self.assertTrue(self.settlement.is_fully_settled)


class BackfillTests(TestCase):
    def test_backfills_only_delivered_orders_without_settlements(self):
        rider = Rider.objects.create(name="Karim")
        delivered = make_order(rider=rider, status=FoodOrder.Status.DELIVERED)
        make_order(rider=rider, status=FoodOrder.Status.PLACED)
        already = make_order(rider=rider, status=FoodOrder.Status.DELIVERED)
        settle_order(already)

        created = backfill_settlements()
        self.assertEqual(created, 1)
        self.assertTrue(OrderSettlement.objects.filter(order=delivered).exists())
        self.assertEqual(OrderSettlement.objects.count(), 2)

    def test_is_safe_to_rerun(self):
        rider = Rider.objects.create(name="Karim")
        make_order(rider=rider, status=FoodOrder.Status.DELIVERED)
        self.assertEqual(backfill_settlements(), 1)
        self.assertEqual(backfill_settlements(), 0)


class CommissionFloorTests(TestCase):
    """max(floor, %) at settlement time, snapshotted so it never moves."""

    def setUp(self):
        self.rider = Rider.objects.create(name="Karim")
        self.r = Restaurant.objects.create(
            name="Floor Co", slug="floor-co",
            commission_percentage=Decimal("12.00"), min_commission_amount=Decimal("25.00"))

    def _order(self, subtotal, **kw):
        return make_order(restaurant=self.r, rider=self.rider, subtotal=Decimal(subtotal),
                          delivery_fee=Decimal("50.00"), tip=Decimal("0.00"),
                          total=Decimal(subtotal) + Decimal("50.00"), **kw)

    def test_the_floor_applies_to_a_small_order(self):
        b = compute_breakdown(self._order("150.00"))
        self.assertEqual(b["commission_amount"], Decimal("25.00"))   # not 18.00

    def test_the_percentage_applies_to_a_large_order(self):
        b = compute_breakdown(self._order("600.00"))
        self.assertEqual(b["commission_amount"], Decimal("72.00"))

    def test_the_books_still_balance_when_the_floor_binds(self):
        """The invariant must not depend on how commission was derived."""
        order = self._order("150.00")
        b = compute_breakdown(order)
        self.assertEqual(
            b["restaurant_payout"] + b["rider_payout"] + b["platform_revenue"], order.total)

    def test_a_tiny_order_never_produces_a_negative_restaurant_payout(self):
        b = compute_breakdown(self._order("20.00"))
        self.assertEqual(b["commission_amount"], Decimal("20.00"))
        self.assertEqual(b["restaurant_payout"], Decimal("0.00"))
        self.assertGreaterEqual(b["restaurant_payout"], Decimal("0.00"))

    def test_the_floor_is_snapshotted_onto_the_settlement(self):
        order = self._order("150.00")
        s = settle_order(order)
        self.assertEqual(s.commission_floor, Decimal("25.00"))

    def test_raising_the_floor_later_does_not_move_past_books(self):
        order = self._order("150.00")
        s = settle_order(order)
        self.r.min_commission_amount = Decimal("90.00")
        self.r.save()
        s.refresh_from_db()
        self.assertEqual(s.commission_amount, Decimal("25.00"))
        self.assertEqual(s.commission_floor, Decimal("25.00"))


class RiderBasePaySnapshotTests(TestCase):
    """Settlement pays the rider what checkout quoted for the distance."""

    def setUp(self):
        self.rider = Rider.objects.create(name="Karim")

    def test_the_orders_quoted_pay_wins_over_the_flat_default(self):
        order = make_order(rider=self.rider, rider_base_pay=Decimal("73.00"),
                           distance_km=Decimal("6.00"))
        b = compute_breakdown(order)
        self.assertEqual(b["rider_base_pay"], Decimal("73.00"))
        self.assertEqual(b["rider_payout"], Decimal("93.00"))   # + the 20 tip

    def test_a_pre_distance_order_still_gets_the_flat_default(self):
        """Orders placed before distance pricing have a 0 snapshot; they must
        not silently pay their rider nothing."""
        order = make_order(rider=self.rider, rider_base_pay=Decimal("0.00"))
        self.assertEqual(compute_breakdown(order)["rider_base_pay"], Decimal("40.00"))

    def test_an_explicit_override_still_wins(self):
        order = make_order(rider=self.rider, rider_base_pay=Decimal("73.00"))
        self.assertEqual(
            compute_breakdown(order, rider_base_pay=Decimal("10.00"))["rider_base_pay"],
            Decimal("10.00"))

    def test_an_unassigned_order_pays_no_one_however_it_was_quoted(self):
        order = make_order(rider=None, rider_base_pay=Decimal("73.00"))
        self.assertEqual(compute_breakdown(order)["rider_base_pay"], Decimal("0.00"))

    def test_the_books_balance_with_a_distance_priced_delivery(self):
        order = make_order(rider=self.rider, rider_base_pay=Decimal("57.00"),
                           delivery_fee=Decimal("80.00"), subtotal=Decimal("500.00"),
                           tip=Decimal("20.00"), total=Decimal("600.00"))
        b = compute_breakdown(order)
        self.assertEqual(
            b["restaurant_payout"] + b["rider_payout"] + b["platform_revenue"], order.total)
        self.assertGreater(b["platform_revenue"], Decimal("0"))
