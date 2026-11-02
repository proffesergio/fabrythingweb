from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from food.models import Restaurant, FoodOrder

User = get_user_model()


def auth(c, u):
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(u).access_token}")


class FulfillmentTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner_a = User.objects.create(username="oa", email="oa@x.com", role="Restaurant")
        self.owner_b = User.objects.create(username="ob", email="ob@x.com", role="Restaurant")
        self.ra = Restaurant.objects.create(owner=self.owner_a, name="A", slug="a", status=Restaurant.Status.ACTIVE)
        self.rb = Restaurant.objects.create(owner=self.owner_b, name="B", slug="b", status=Restaurant.Status.ACTIVE)
        self.order_a = FoodOrder.objects.create(restaurant=self.ra, guest_name="G", guest_phone="1",
                                                delivery_address="a", subtotal=1, delivery_fee=0, tip=0, total=1)

    def test_vendor_lists_only_own_orders(self):
        FoodOrder.objects.create(restaurant=self.rb, guest_name="G", guest_phone="1",
                                 delivery_address="a", subtotal=1, delivery_fee=0, tip=0, total=1)
        auth(self.client, self.owner_a)
        res = self.client.get("/api/food/vendor/orders/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()["data"]), 1)

    def test_vendor_advances_own_order_status(self):
        auth(self.client, self.owner_a)
        res = self.client.patch(f"/api/food/vendor/orders/{self.order_a.id}/status/",
                                {"status": "CONFIRMED"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.order_a.refresh_from_db()
        self.assertEqual(self.order_a.status, "CONFIRMED")

    def test_vendor_cannot_touch_other_restaurant_order(self):
        auth(self.client, self.owner_b)
        res = self.client.patch(f"/api/food/vendor/orders/{self.order_a.id}/status/",
                                {"status": "CONFIRMED"}, format="json")
        self.assertIn(res.status_code, (403, 404))
        self.order_a.refresh_from_db()
        self.assertEqual(self.order_a.status, "PLACED")

    def test_illegal_transition_rejected(self):
        auth(self.client, self.owner_a)
        res = self.client.patch(f"/api/food/vendor/orders/{self.order_a.id}/status/",
                                {"status": "DELIVERED"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_admin_lists_all_orders(self):
        admin = User.objects.create(username="adm", email="adm@x.com", role="Admin")
        FoodOrder.objects.create(restaurant=self.rb, guest_name="G", guest_phone="1",
                                 delivery_address="a", subtotal=1, delivery_fee=0, tip=0, total=1)
        auth(self.client, admin)
        res = self.client.get("/api/food/admin/orders/")
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(len(res.json()["data"]), 2)
