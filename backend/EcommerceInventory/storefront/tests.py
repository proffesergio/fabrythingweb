from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from orders.models import Order

User = get_user_model()


def auth(c, u):
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(u).access_token}")


class AdminCustomerListTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create(username="adm", email="adm@x.com", role="Admin")
        self.cust = User.objects.create(username="karim", email="karim@x.com", role="Customer", phone="017")
        Order.objects.create(customer=self.cust, subtotal=Decimal("100"), shipping_amount=Decimal("0"),
                             total_amount=Decimal("100"), contact_name="Karim", contact_phone="017",
                             shipping_address={"address": "x"})

    def test_lists_customers_with_order_counts(self):
        auth(self.client, self.admin)
        res = self.client.get("/api/store/admin/customers/")
        self.assertEqual(res.status_code, 200, res.content)
        rows = res.json()["data"]["data"]
        row = next(r for r in rows if r["username"] == "karim")
        self.assertEqual(row["order_count"], 1)
        self.assertEqual(Decimal(str(row["total_spent"])), Decimal("100"))

    def test_search_filters_customers(self):
        auth(self.client, self.admin)
        res = self.client.get("/api/store/admin/customers/?search=karim")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(all("karim" in r["username"].lower() or "karim" in (r["email"] or "").lower()
                            for r in res.json()["data"]["data"]))
