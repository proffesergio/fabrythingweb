from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from food.models import Restaurant, FoodOrder

User = get_user_model()


def auth(c, u):
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(u).access_token}")


class AdminOrderDetailTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create(username="adm", email="adm@x.com", role="Admin")
        self.r = Restaurant.objects.create(name="R", slug="r", status=Restaurant.Status.ACTIVE)
        self.order = FoodOrder.objects.create(restaurant=self.r, guest_name="G", guest_phone="1",
                                              delivery_address="a", subtotal=1, delivery_fee=0, tip=0, total=1)

    def test_admin_gets_detail_with_transitions(self):
        auth(self.client, self.admin)
        res = self.client.get(f"/api/food/admin/orders/{self.order.id}/")
        self.assertEqual(res.status_code, 200, res.content)
        d = res.json()["data"]
        self.assertEqual(d["order_code"], self.order.order_code)
        self.assertIn("CONFIRMED", d["allowed_transitions"])

    def test_missing_order_404(self):
        auth(self.client, self.admin)
        self.assertEqual(self.client.get("/api/food/admin/orders/999999/").status_code, 404)

    def test_non_admin_403(self):
        cust = User.objects.create(username="c", email="c@x.com", role="Customer")
        auth(self.client, cust)
        self.assertEqual(self.client.get(f"/api/food/admin/orders/{self.order.id}/").status_code, 403)
