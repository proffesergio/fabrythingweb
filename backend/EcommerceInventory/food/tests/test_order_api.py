from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from food.models import (Restaurant, RestaurantHours, DeliveryZone, RestaurantZone,
                         FoodCategory, FoodItem)

User = get_user_model()


def auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")


class OrderApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.zone = DeliveryZone.objects.create(name="Z", center_lat="23.8", center_lng="90.4", radius_km="5")
        self.r = Restaurant.objects.create(name="R", slug="r", status=Restaurant.Status.ACTIVE,
                                           is_open=True, base_delivery_fee=Decimal("30.00"),
                                           min_order_amount=Decimal("0.00"))
        RestaurantZone.objects.create(restaurant=self.r, zone=self.zone)
        for wd in range(7):
            RestaurantHours.objects.create(restaurant=self.r, weekday=wd, open_time="00:00", close_time="23:59")
        self.cat = FoodCategory.objects.create(restaurant=self.r, name="Main")
        self.item = FoodItem.objects.create(restaurant=self.r, category_id=self.cat,
                                            name="Biriyani", slug="biriyani", price=Decimal("120.00"))

    def _payload(self, **over):
        p = {"restaurant_slug": "r", "zone_id": self.zone.id, "contact_name": "A",
             "contact_phone": "017", "delivery_address": "addr",
             "items": [{"item_id": self.item.id, "quantity": 1, "option_ids": []}]}
        p.update(over); return p

    def test_guest_can_place_cod_order(self):
        res = self.client.post("/api/food/orders/", self._payload(), format="json")
        self.assertEqual(res.status_code, 201, res.content)
        d = res.json()["data"]
        self.assertTrue(d["order_code"].startswith("FD-"))
        self.assertEqual(Decimal(str(d["total"])), Decimal("150.00"))

    def test_server_ignores_client_supplied_total(self):
        res = self.client.post("/api/food/orders/", self._payload(total="1.00", subtotal="1.00"), format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(Decimal(str(res.json()["data"]["total"])), Decimal("150.00"))

    def test_guest_track_requires_matching_phone(self):
        code = self.client.post("/api/food/orders/", self._payload(), format="json").json()["data"]["order_code"]
        ok = self.client.get(f"/api/food/orders/{code}/?phone=017")
        self.assertEqual(ok.status_code, 200)
        bad = self.client.get(f"/api/food/orders/{code}/?phone=999")
        self.assertIn(bad.status_code, (403, 404))

    def test_auth_history_lists_only_own(self):
        u = User.objects.create(username="cust", email="cust@x.com", role="Customer")
        auth(self.client, u)
        self.client.post("/api/food/orders/", self._payload(), format="json")
        res = self.client.get("/api/food/orders/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()["data"]), 1)

    def test_below_min_order_returns_400(self):
        self.r.min_order_amount = Decimal("500.00"); self.r.save()
        res = self.client.post("/api/food/orders/", self._payload(), format="json")
        self.assertEqual(res.status_code, 400)
