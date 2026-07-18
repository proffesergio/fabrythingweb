from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from food.models import Restaurant, FoodCategory

User = get_user_model()


def auth(client, user):
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


class VendorScopingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Users.email is unique with no default; give each test user a distinct
        # address so setUp doesn't collide on "" (an unrelated model constraint,
        # not part of what this test is verifying).
        self.owner_a = User.objects.create(username="a", email="a@example.com", role="Restaurant")
        self.owner_b = User.objects.create(username="b", email="b@example.com", role="Restaurant")
        self.ra = Restaurant.objects.create(owner=self.owner_a, name="A", slug="a")
        self.rb = Restaurant.objects.create(owner=self.owner_b, name="B", slug="b")
        self.cat_b = FoodCategory.objects.create(restaurant=self.rb, name="B-cat")

    def test_vendor_lists_only_own_categories(self):
        FoodCategory.objects.create(restaurant=self.ra, name="A-cat")
        auth(self.client, self.owner_a)
        res = self.client.get("/api/food/vendor/categories/")
        names = [c["name"] for c in res.json()["data"]]
        self.assertEqual(names, ["A-cat"])

    def test_vendor_cannot_edit_others_category(self):
        auth(self.client, self.owner_a)
        res = self.client.patch(f"/api/food/vendor/categories/{self.cat_b.id}/",
                                {"name": "hacked"}, format="json")
        self.assertIn(res.status_code, (403, 404))
        self.cat_b.refresh_from_db()
        self.assertEqual(self.cat_b.name, "B-cat")

    def test_non_restaurant_role_blocked(self):
        customer = User.objects.create(username="c", email="c@example.com", role="Customer")
        auth(self.client, customer)
        res = self.client.get("/api/food/vendor/categories/")
        self.assertEqual(res.status_code, 403)
