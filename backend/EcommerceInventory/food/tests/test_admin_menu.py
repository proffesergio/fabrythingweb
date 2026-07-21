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

    def _item_payload(self, **over):
        base = {"restaurant": self.r.id, "category_id": self.cat.id,
                "name": "Beef Tehari", "price": "180.00"}
        base.update(over)
        return base

    def test_create_item_with_tags_schedule_and_spice(self):
        """The full 'additional info' payload the admin UI sends must be accepted."""
        auth(self.client, self.admin)
        res = self.client.post("/api/food/admin/items/", self._item_payload(
            tags=["spicy", "bestseller"], spice_level="Hot",
            available_from="08:00", available_to="11:00", available_days=[0, 1, 2],
            is_featured=True, image="https://cdn.example.com/tehari.jpg",
        ), format="json")
        self.assertEqual(res.status_code, 201, res.content)
        item = FoodItem.objects.get(name="Beef Tehari")
        self.assertEqual(item.tags, ["spicy", "bestseller"])
        self.assertEqual(item.available_days, [0, 1, 2])

    def test_blank_optional_fields_are_treated_as_unset(self):
        """The dialog sends "" for untouched optional fields; that must mean null."""
        auth(self.client, self.admin)
        res = self.client.post("/api/food/admin/items/", self._item_payload(
            discount_price="", prep_minutes="", available_from="", available_to="",
        ), format="json")
        self.assertEqual(res.status_code, 201, res.content)
        item = FoodItem.objects.get(name="Beef Tehari")
        self.assertIsNone(item.discount_price)
        self.assertIsNone(item.prep_minutes)
        self.assertIsNone(item.available_from)

    def test_optional_fields_can_be_cleared_on_edit(self):
        auth(self.client, self.admin)
        item = FoodItem.objects.create(restaurant=self.r, category_id=self.cat, name="X", slug="x",
                                       price=Decimal("100"), discount_price=Decimal("80"))
        res = self.client.patch(f"/api/food/admin/items/{item.id}/",
                                {"discount_price": None}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        item.refresh_from_db()
        self.assertIsNone(item.discount_price)

    def test_bad_image_reports_the_image_field(self):
        """A non-URL image must fail on 'image' specifically, so the UI can point at it."""
        auth(self.client, self.admin)
        res = self.client.post("/api/food/admin/items/",
                               self._item_payload(image="tehari.jpg"), format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("image", res.json()["field_errors"])

    def test_unknown_tag_is_rejected_readably(self):
        auth(self.client, self.admin)
        res = self.client.post("/api/food/admin/items/",
                               self._item_payload(tags=["gluten-free"]), format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("tags", res.json()["field_errors"])

    def test_available_day_out_of_range_is_rejected(self):
        auth(self.client, self.admin)
        res = self.client.post("/api/food/admin/items/",
                               self._item_payload(available_days=[9]), format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("available_days", res.json()["field_errors"])

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
