from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from food.models import Restaurant, FoodCategory, FoodItem, FoodItemOptionGroup, FoodItemOption

User = get_user_model()


def auth(c, u):
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(u).access_token}")


class AdminMenuTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create(username="adm", email="adm@x.com", role="Admin")
        self.r = Restaurant.objects.create(name="R", slug="r", status=Restaurant.Status.ACTIVE)
        self.cat = FoodCategory.objects.create(restaurant=self.r, name="Main")

    def test_customer_blocked(self):
        cust = User.objects.create(username="c", email="c@x.com", role="Customer")
        auth(self.client, cust)
        res = self.client.get(f"/api/food/admin/categories/?restaurant={self.r.id}")
        self.assertEqual(res.status_code, 403)

    def test_admin_creates_category_for_chosen_restaurant(self):
        auth(self.client, self.admin)
        res = self.client.post("/api/food/admin/categories/",
                               {"restaurant": self.r.id, "name": "Drinks"}, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertTrue(FoodCategory.objects.filter(restaurant=self.r, name="Drinks").exists())

    def test_admin_lists_items_scoped_to_restaurant(self):
        r2 = Restaurant.objects.create(name="R2", slug="r2")
        c2 = FoodCategory.objects.create(restaurant=r2, name="C2")
        FoodItem.objects.create(restaurant=self.r, category_id=self.cat, name="Mine", slug="mine", price=Decimal("10"))
        FoodItem.objects.create(restaurant=r2, category_id=c2, name="Other", slug="other", price=Decimal("10"))
        auth(self.client, self.admin)
        res = self.client.get(f"/api/food/admin/items/?restaurant={self.r.id}")
        names = [i["name"] for i in res.json()["data"]]
        self.assertEqual(names, ["Mine"])

    def test_admin_creates_item_autoslug(self):
        auth(self.client, self.admin)
        res = self.client.post("/api/food/admin/items/",
                               {"restaurant": self.r.id, "category_id": self.cat.id,
                                "name": "Chicken Roll", "price": "90.00"}, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()["data"]["slug"], "chicken-roll")

    def test_admin_creates_option_group_and_option(self):
        item = FoodItem.objects.create(restaurant=self.r, category_id=self.cat, name="Burger", slug="burger", price=Decimal("100"))
        auth(self.client, self.admin)
        g = self.client.post("/api/food/admin/option-groups/",
                             {"item": item.id, "name": "Size", "max_select": 1}, format="json")
        self.assertEqual(g.status_code, 201, g.content)
        gid = g.json()["data"]["id"]
        o = self.client.post("/api/food/admin/options/",
                             {"group": gid, "name": "Large", "price_delta": "50.00"}, format="json")
        self.assertEqual(o.status_code, 201, o.content)
        self.assertTrue(FoodItemOption.objects.filter(group_id=gid, name="Large").exists())
