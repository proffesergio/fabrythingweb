"""The whole path, in one test: browse → quote → order → dispatch offer →
rider accepts → delivers → settlement + rider pay + cash all agree.

This is the ship gate for the marketplace release. Each layer has its own unit
tests; this proves they compose into one working order, and that the money the
customer paid is exactly the money split three ways at the end.
"""
from datetime import time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from food.models import (DeliveryZone, FoodCategory, FoodItem, FoodOrder, OrderSettlement,
                         Restaurant, RestaurantHours, Rider)
from food.services_cash import cash_in_hand, record_deposit

User = get_user_model()
LAT, LNG = Decimal("23.770000"), Decimal("90.780000")


def at_km_north(km):
    return LAT + Decimal(str(round(km / 111.0, 6))), LNG


class FullJourneyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.zone = DeliveryZone.objects.create(name="Bancharampur Sadar", name_bn="বাঞ্ছারামপুর সদর",
                                                center_lat=LAT, center_lng=LNG, radius_km=Decimal("20"))
        self.restaurant = Restaurant.objects.create(
            name="Dhaka Fast Food", slug="dhaka-fast-food", status=Restaurant.Status.ACTIVE,
            pickup_lat=LAT, pickup_lng=LNG, commission_percentage=Decimal("12.00"),
            min_commission_amount=Decimal("25.00"), avg_prep_minutes=25)
        RestaurantHours.objects.create(restaurant=self.restaurant,
                                       weekday=timezone.localtime().weekday(),
                                       open_time=time(0, 0), close_time=time(23, 59))
        cat = FoodCategory.objects.create(restaurant=self.restaurant, name="Burgers")
        self.item = FoodItem.objects.create(restaurant=self.restaurant, category_id=cat,
                                            name="Beef Burger", slug="beef-burger",
                                            price=Decimal("250.00"), is_available=True)

    def _rider_client(self, rider):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(rider.user).access_token}")
        return c

    def _admin_client(self):
        admin = User.objects.create_user(username="boss", email="boss@x.com", password="x", role="Admin")
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(admin).access_token}")
        return c

    def test_a_whole_order_from_browse_to_paid_out(self):
        # 1. BROWSE — the restaurant is visible and reads as open.
        rows = self.client.get("/api/food/restaurants/").json()["data"]["data"]
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["is_open_now"])

        # 2. QUOTE — the customer sees the delivery fee before committing.
        dlat, dlng = at_km_north(6.0)
        quote = self.client.get("/api/food/delivery-quote/", {
            "restaurant": "dhaka-fast-food", "zone": self.zone.id,
            "lat": str(dlat), "lng": str(dlng)}).json()["data"]
        self.assertTrue(quote["deliverable"])
        self.assertEqual(quote["fee"], "80.00")   # distance-priced

        # 3. ORDER — placed as a guest, priced identically to the quote.
        placed = self.client.post("/api/food/orders/", {
            "restaurant_slug": "dhaka-fast-food", "contact_name": "Rahim", "contact_phone": "017",
            "delivery_address": "Field 3", "zone_id": self.zone.id,
            "delivery_lat": str(dlat), "delivery_lng": str(dlng), "tip": "10.00",
            "items": [{"item_id": self.item.id, "quantity": 1, "option_ids": []}],
        }, format="json")
        self.assertEqual(placed.status_code, 201, placed.content)
        code = placed.json()["data"]["order_code"]
        order = FoodOrder.objects.get(order_code=code)
        self.assertEqual(order.delivery_fee, Decimal("80.00"))
        self.assertEqual(order.total, Decimal("340.00"))   # 250 + 80 + 10 tip

        # A rider comes online.
        rider = Rider.objects.create(
            user=User.objects.create(username="karim", email="k@x.com", role="Rider"),
            name="Karim", is_available=True, last_seen_at=timezone.now(),
            current_lat=LAT, current_lng=LNG)
        rc = self._rider_client(rider)

        # 4. DISPATCH — admin confirms; the order is OFFERED, not yet assigned.
        admin = self._admin_client()
        admin.patch(f"/api/food/admin/orders/{order.id}/status/",
                    {"status": "CONFIRMED"}, format="json")
        order.refresh_from_db()
        self.assertIsNone(order.rider)

        offer = rc.get("/api/food/rider/offer/").json()["data"]["offer"]
        self.assertEqual(offer["order_code"], code)
        # The offer shows the distance-priced pay: the snapshot + the tip. Assert
        # it against the snapshot rather than a constant, since the exact km (and
        # so the base) depends on the haversine.
        expected_pay = order.rider_base_pay + order.tip
        self.assertEqual(offer["rider_pay"], str(expected_pay))
        self.assertGreater(order.rider_base_pay, Decimal("55"))   # ~6km priced, not the flat rate

        # 5. ACCEPT — now the rider owns it.
        rc.post("/api/food/rider/offer/", {"action": "accept"}, format="json")
        order.refresh_from_db()
        self.assertEqual(order.rider, rider)

        # 6. DELIVER — rider walks it forward to DELIVERED.
        for status in ["PREPARING", "OUT_FOR_DELIVERY", "DELIVERED"]:
            res = rc.patch(f"/api/food/rider/orders/{order.id}/status/",
                           {"status": status}, format="json")
            self.assertEqual(res.status_code, 200, res.content)
        order.refresh_from_db()
        self.assertEqual(order.status, "DELIVERED")

        # 7. SETTLEMENT — the books balance against what the customer paid, and
        #    the platform is in profit on the delivery.
        s = OrderSettlement.objects.get(order=order)
        self.assertEqual(s.commission_amount, Decimal("30.00"))   # 12% of 250
        self.assertEqual(s.rider_base_pay, order.rider_base_pay)  # the distance snapshot, not a flat guess
        self.assertEqual(s.restaurant_payout + s.rider_payout + s.platform_revenue, order.total)
        self.assertGreater(s.platform_revenue, Decimal("0"))

        # The rider's dashboard pay matches the settlement exactly.
        earn = rc.get("/api/food/rider/earnings/").json()["data"]
        self.assertEqual(earn["lifetime"], str(order.rider_base_pay + order.tip))

        # 8. CASH — the rider is holding the COD money until they deposit it.
        self.assertEqual(cash_in_hand(rider), Decimal("340.00"))
        record_deposit(rider, "340.00")
        self.assertEqual(cash_in_hand(rider), Decimal("0.00"))

    def test_declined_then_delivered_by_the_next_rider(self):
        """The cascade end to end: first rider says no, second delivers."""
        order = FoodOrder.objects.create(
            guest_name="G", guest_phone="017", delivery_address="A", restaurant=self.restaurant,
            zone=self.zone, subtotal=Decimal("250"), delivery_fee=Decimal("40"),
            rider_base_pay=Decimal("35"), total=Decimal("290"), status=FoodOrder.Status.CONFIRMED)

        def rider(name, km):
            lat, lng = at_km_north(km)
            r = Rider.objects.create(
                user=User.objects.create(username=name, email=f"{name}@x.com", role="Rider"),
                name=name, is_available=True, last_seen_at=timezone.now(),
                current_lat=lat, current_lng=lng)
            return r, self._rider_client(r)

        r1, c1 = rider("first", 0.3)
        r2, c2 = rider("second", 2)

        from food.services_dispatch import offer_order
        offer_order(order)

        # Nearest gets it, declines; it cascades to the next.
        self.assertEqual(c1.get("/api/food/rider/offer/").json()["data"]["offer"]["order_code"],
                         order.order_code)
        c1.post("/api/food/rider/offer/", {"action": "decline"}, format="json")

        self.assertEqual(c2.get("/api/food/rider/offer/").json()["data"]["offer"]["order_code"],
                         order.order_code)
        c2.post("/api/food/rider/offer/", {"action": "accept"}, format="json")

        order.refresh_from_db()
        self.assertEqual(order.rider, r2)
        # And the decliner has nothing on their plate.
        self.assertEqual(c1.get("/api/food/rider/orders/").json()["data"], [])
