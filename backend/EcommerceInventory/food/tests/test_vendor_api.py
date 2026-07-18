from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from food.models import Restaurant, FoodCategory, FoodItem

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

    def test_vendor_cannot_create_item_with_others_category(self):
        auth(self.client, self.owner_a)
        payload = {
            "category_id": self.cat_b.id,
            "name": "Hacked Item",
            "slug": "hacked-item",
            "price": "10.00",
        }
        res = self.client.post("/api/food/vendor/items/", payload, format="json")
        self.assertIn(res.status_code, (400, 403))
        self.assertFalse(FoodItem.objects.filter(category_id=self.cat_b, name="Hacked Item").exists())

    def test_vendor_cannot_update_item_to_others_category(self):
        cat_a = FoodCategory.objects.create(restaurant=self.ra, name="A-cat-2")
        item_a = FoodItem.objects.create(
            restaurant=self.ra, category_id=cat_a, name="A Item", slug="a-item", price=Decimal("5.00"),
        )
        auth(self.client, self.owner_a)
        res = self.client.patch(
            f"/api/food/vendor/items/{item_a.id}/", {"category_id": self.cat_b.id}, format="json",
        )
        self.assertIn(res.status_code, (400, 403))
        item_a.refresh_from_db()
        self.assertEqual(item_a.category_id_id, cat_a.id)


class VendorRestaurantProfileTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner_a = User.objects.create(username="ra_owner", email="ra_owner@example.com", role="Restaurant")
        self.owner_b = User.objects.create(username="rb_owner", email="rb_owner@example.com", role="Restaurant")
        self.ra = Restaurant.objects.create(
            owner=self.owner_a, name="Restaurant A", slug="restaurant-a",
            commission_percentage=Decimal("15.00"), status=Restaurant.Status.ACTIVE,
        )
        self.rb = Restaurant.objects.create(owner=self.owner_b, name="Restaurant B", slug="restaurant-b")

    def test_get_returns_own_restaurant(self):
        auth(self.client, self.owner_a)
        res = self.client.get("/api/food/vendor/restaurant/")
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertEqual(data["name"], "Restaurant A")
        self.assertEqual(data["slug"], "restaurant-a")

    def test_patch_can_update_editable_fields(self):
        auth(self.client, self.owner_a)
        res = self.client.patch(
            "/api/food/vendor/restaurant/", {"is_open": False, "phone": "0170000000"}, format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.ra.refresh_from_db()
        self.assertFalse(self.ra.is_open)
        self.assertEqual(self.ra.phone, "0170000000")

    def test_patch_cannot_change_readonly_fields(self):
        auth(self.client, self.owner_a)
        res = self.client.patch(
            "/api/food/vendor/restaurant/",
            {"commission_percentage": "0.00", "status": Restaurant.Status.SUSPENDED, "slug": "hacked-slug"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.ra.refresh_from_db()
        self.assertEqual(self.ra.commission_percentage, Decimal("15.00"))
        self.assertEqual(self.ra.status, Restaurant.Status.ACTIVE)
        self.assertEqual(self.ra.slug, "restaurant-a")

    def test_non_restaurant_role_blocked(self):
        customer = User.objects.create(username="rp_customer", email="rp_customer@example.com", role="Customer")
        auth(self.client, customer)
        res = self.client.get("/api/food/vendor/restaurant/")
        self.assertEqual(res.status_code, 403)
