from decimal import Decimal
from datetime import time, datetime
from django.test import TestCase
from django.contrib.auth import get_user_model
from food.models import Restaurant, RestaurantHours

User = get_user_model()


class RestaurantLogicTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create(username="vendor1", role="Restaurant")
        self.r = Restaurant.objects.create(
            owner=self.owner, name="Rahim Hotel", slug="rahim-hotel",
            pickup_lat=Decimal("23.81"), pickup_lng=Decimal("90.41"),
            commission_percentage=Decimal("15.00"), base_delivery_fee=Decimal("30.00"),
            status=Restaurant.Status.ACTIVE, is_open=True,
        )

    def test_payout_subtracts_commission(self):
        # 15% commission on 1000 -> payout 850
        self.assertEqual(self.r.payout_for(Decimal("1000.00")), Decimal("850.00"))

    def test_closed_when_toggle_off(self):
        self.r.is_open = False
        self.assertFalse(self.r.is_currently_open(datetime(2026, 7, 20, 12, 0)))  # Monday noon

    def test_open_within_hours(self):
        # Monday = weekday 0 in our model
        RestaurantHours.objects.create(
            restaurant=self.r, weekday=0, open_time=time(9, 0), close_time=time(22, 0),
        )
        self.assertTrue(self.r.is_currently_open(datetime(2026, 7, 20, 12, 0)))

    def test_closed_outside_hours(self):
        RestaurantHours.objects.create(
            restaurant=self.r, weekday=0, open_time=time(9, 0), close_time=time(11, 0),
        )
        self.assertFalse(self.r.is_currently_open(datetime(2026, 7, 20, 12, 0)))
