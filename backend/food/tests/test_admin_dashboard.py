from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from food.models import Restaurant, FoodOrder

User = get_user_model()


def auth(c, u):
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(u).access_token}")


class AdminDashboardTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create(username="adm", email="adm@x.com", role="Admin")
        self.active = Restaurant.objects.create(name="A", slug="a", status=Restaurant.Status.ACTIVE)
        self.pending = Restaurant.objects.create(name="P", slug="p", status=Restaurant.Status.PENDING)
        FoodOrder.objects.create(restaurant=self.active, guest_name="G", guest_phone="1",
                                 delivery_address="a", subtotal=Decimal("100"), delivery_fee=Decimal("20"),
                                 tip=0, total=Decimal("120"), status=FoodOrder.Status.DELIVERED)
        FoodOrder.objects.create(restaurant=self.active, guest_name="G", guest_phone="1",
                                 delivery_address="a", subtotal=Decimal("50"), delivery_fee=Decimal("20"),
                                 tip=0, total=Decimal("70"), status=FoodOrder.Status.CANCELLED)

    def test_non_admin_blocked(self):
        cust = User.objects.create(username="c", email="c@x.com", role="Customer")
        auth(self.client, cust)
        res = self.client.get("/api/food/admin/dashboard/")
        self.assertEqual(res.status_code, 403)

    def test_dashboard_returns_stats(self):
        auth(self.client, self.admin)
        res = self.client.get("/api/food/admin/dashboard/")
        self.assertEqual(res.status_code, 200, res.content)
        d = res.json()["data"]
        self.assertEqual(d["orders"]["total"], 2)
        self.assertEqual(d["restaurants"]["active"], 1)
        self.assertEqual(d["restaurants"]["pending"], 1)
        # revenue excludes the cancelled order (120 counted, 70 excluded)
        self.assertEqual(Decimal(str(d["revenue"]["this_month"])), Decimal("120.00"))
        self.assertIn("revenue_trend", d)
        self.assertIn("recent_orders", d)
