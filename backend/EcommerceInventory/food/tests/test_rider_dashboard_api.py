from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from food.models import Rider, Restaurant, FoodOrder, FoodOrderItem, RiderEarning

User = get_user_model()


def auth(c, u):
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(u).access_token}")


class RiderHeartbeatTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username="rdr", email="rdr@x.com", role="Rider")
        self.rider = Rider.objects.create(user=self.user, name="Rakib")

    def test_heartbeat_records_position_and_time(self):
        # Heartbeat only persists coordinates once the rider has opted in to
        # sharing (Task 4: location-privacy, default is NOT shared).
        self.rider.is_sharing_location = True
        self.rider.save(update_fields=["is_sharing_location"])
        auth(self.client, self.user)
        res = self.client.post("/api/food/rider/heartbeat/",
                               {"lat": 23.7104, "lng": 90.9280}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.rider.refresh_from_db()
        self.assertAlmostEqual(float(self.rider.current_lat), 23.7104, places=4)
        self.assertAlmostEqual(float(self.rider.current_lng), 90.9280, places=4)
        self.assertIsNotNone(self.rider.last_seen_at)

    def test_heartbeat_without_coordinates_still_refreshes_presence(self):
        auth(self.client, self.user)
        res = self.client.post("/api/food/rider/heartbeat/", {}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.rider.refresh_from_db()
        self.assertIsNotNone(self.rider.last_seen_at)
        self.assertIsNone(self.rider.current_lat)

    def test_non_rider_is_blocked(self):
        cust = User.objects.create(username="c", email="c@x.com", role="Customer")
        auth(self.client, cust)
        res = self.client.post("/api/food/rider/heartbeat/", {"lat": 1, "lng": 1}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_rider_me_exposes_presence(self):
        self.rider.last_seen_at = timezone.now()
        self.rider.current_lat, self.rider.current_lng = Decimal("23.7"), Decimal("90.9")
        self.rider.save()
        auth(self.client, self.user)
        res = self.client.get("/api/food/rider/me/")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertIn("last_seen_at", res.json()["data"])


class RiderOrderPayloadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username="rdr", email="rdr@x.com", role="Rider")
        self.rider = Rider.objects.create(user=self.user, name="Rakib")
        self.restaurant = Restaurant.objects.create(
            name="Kacchi Ghor", slug="kacchi-ghor", status=Restaurant.Status.ACTIVE,
            pickup_lat=Decimal("23.710400"), pickup_lng=Decimal("90.928000"),
            phone="01711000000", address="Bancharampur Bazar",
        )
        self.order = FoodOrder.objects.create(
            guest_name="Karim", guest_phone="01811000000", delivery_address="Ujanchar",
            restaurant=self.restaurant, rider=self.rider, subtotal=Decimal("300"),
            total=Decimal("340"), status=FoodOrder.Status.OUT_FOR_DELIVERY,
            payment_method="COD", payment_status="PENDING", notes="Extra salad please",
        )
        FoodOrderItem.objects.create(order=self.order, item_name="Kacchi", unit_price=Decimal("300"),
                                     quantity=1, line_total=Decimal("300"),
                                     selected_options=[{"name": "Extra meat", "price_delta": "40.00"}])

    def test_order_payload_carries_pickup_contact_notes_and_cash(self):
        auth(self.client, self.user)
        res = self.client.get("/api/food/rider/orders/")
        self.assertEqual(res.status_code, 200, res.content)
        order = res.json()["data"][0]
        self.assertEqual(order["pickup_lat"], "23.710400")
        self.assertEqual(order["restaurant_phone"], "01711000000")
        self.assertEqual(order["restaurant_address"], "Bancharampur Bazar")
        self.assertEqual(order["notes"], "Extra salad please")
        self.assertEqual(order["cash_to_collect"], "340.00")
        self.assertEqual(order["items"][0]["selected_options"][0]["name"], "Extra meat")

    def test_cash_to_collect_is_zero_for_a_paid_order(self):
        self.order.payment_method = "BKASH"
        self.order.payment_status = "COLLECTED"
        self.order.save()
        auth(self.client, self.user)
        res = self.client.get("/api/food/rider/orders/")
        self.assertEqual(res.json()["data"][0]["cash_to_collect"], "0.00")


class RiderEarningsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username="rdr", email="rdr@x.com", role="Rider")
        self.rider = Rider.objects.create(user=self.user, name="Rakib")
        self.restaurant = Restaurant.objects.create(name="R", slug="r",
                                                    status=Restaurant.Status.ACTIVE)

    def test_earnings_totals_and_history(self):
        delivered = FoodOrder.objects.create(
            guest_name="G", guest_phone="017", delivery_address="A",
            restaurant=self.restaurant, rider=self.rider, subtotal=Decimal("100"),
            total=Decimal("120"), status=FoodOrder.Status.DELIVERED,
        )
        RiderEarning.objects.create(rider=self.rider, order=delivered,
                                    base_pay=Decimal("40.00"), tip=Decimal("10.00"))
        auth(self.client, self.user)
        res = self.client.get("/api/food/rider/earnings/")
        self.assertEqual(res.status_code, 200, res.content)
        data = res.json()["data"]
        self.assertEqual(data["today"], "50.00")
        self.assertEqual(data["lifetime"], "50.00")
        self.assertEqual(data["history"][0]["order_code"], delivered.order_code)
        self.assertEqual(data["history"][0]["payout"], "50.00")

    def test_cash_to_collect_sums_unpaid_cod_orders(self):
        FoodOrder.objects.create(
            guest_name="G", guest_phone="017", delivery_address="A",
            restaurant=self.restaurant, rider=self.rider, subtotal=Decimal("100"),
            total=Decimal("150"), status=FoodOrder.Status.OUT_FOR_DELIVERY,
            payment_method="COD", payment_status="PENDING",
        )
        auth(self.client, self.user)
        res = self.client.get("/api/food/rider/earnings/")
        self.assertEqual(res.json()["data"]["cash_to_collect"], "150.00")
