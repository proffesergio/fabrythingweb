"""CommonListAPIMixin.common_list_decorator is shared by many admin list
endpoints (products, reviews, questions, food, purchase orders, warehouses,
users...). The fix for the storefront 500 (raw `ordering` query param passed
straight to order_by()) must not change behaviour for a *valid* ordering on
any of them -- pinned here against the admin product list.
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Users
from catalog.models import Categories, Products


def auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")


def make_product(owner, category, slug, sku, name):
    return Products.objects.create(
        name=name, slug=slug, description="d", sku=sku,
        initial_buying_price=100, initial_selling_price=100,
        category_id=category, domain_user_id=owner, added_by_user_id=owner,
        status="ACTIVE",
    )


class AdminProductListOrderingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = Users.objects.create_user(
            username="ord-admin-owner", email="ord-admin-owner@x.com", password="x",
            role="Super Admin", country="Bangladesh")
        auth(self.client, self.owner)
        self.category = Categories.objects.create(
            name="Gadgets", slug="admin-ord-gadgets", description="d",
            domain_user_id=self.owner, added_by_user_id=self.owner)
        make_product(self.owner, self.category, "admin-ord-b", "ADM-ORD-B", "Bravo")
        make_product(self.owner, self.category, "admin-ord-a", "ADM-ORD-A", "Alpha")

    def test_valid_ordering_by_name_still_sorts(self):
        res = self.client.get("/api/products/?ordering=name")
        self.assertEqual(res.status_code, 200, res.content)
        names = [r["name"] for r in res.json()["data"]["data"]]
        self.assertEqual(names, ["Alpha", "Bravo"])

    def test_valid_ordering_by_name_descending_still_sorts(self):
        res = self.client.get("/api/products/?ordering=-name")
        self.assertEqual(res.status_code, 200, res.content)
        names = [r["name"] for r in res.json()["data"]["data"]]
        self.assertEqual(names, ["Bravo", "Alpha"])

    def test_garbage_ordering_does_not_500_on_admin_list_either(self):
        res = self.client.get("/api/products/?ordering=not_a_real_field")
        self.assertEqual(res.status_code, 200, res.content)
