from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from food.models import (
    Restaurant, FoodCategory, FoodItem, FoodItemOptionGroup, FoodItemOption,
)
from food.services_menu_copy import copy_menu

User = get_user_model()


def auth(c, u):
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(u).access_token}")


class MenuCopyServiceTests(TestCase):
    def setUp(self):
        self.src = Restaurant.objects.create(name="Source", slug="source",
                                             status=Restaurant.Status.ACTIVE)
        self.dst = Restaurant.objects.create(name="Target", slug="target",
                                             status=Restaurant.Status.ACTIVE)
        self.cat = FoodCategory.objects.create(restaurant=self.src, name="Rice")
        self.item = FoodItem.objects.create(restaurant=self.src, category_id=self.cat,
                                            name="Kacchi", slug="kacchi", price=Decimal("300"),
                                            tags=["bestseller"], spice_level="Hot",
                                            image="https://cdn.example.com/k.jpg")
        group = FoodItemOptionGroup.objects.create(item=self.item, name="Size", max_select=1)
        FoodItemOption.objects.create(group=group, name="Full", price_delta=Decimal("50"))

    def test_full_copy_reproduces_categories_items_and_options(self):
        result = copy_menu(self.src, self.dst)
        self.assertEqual(result["categories_created"], 1)
        self.assertEqual(result["items_copied"], 1)
        self.assertEqual(result["options_copied"], 1)

        copied = FoodItem.objects.get(restaurant=self.dst, name="Kacchi")
        self.assertEqual(copied.price, Decimal("300"))
        self.assertEqual(copied.tags, ["bestseller"])
        self.assertEqual(copied.image, "https://cdn.example.com/k.jpg")
        self.assertEqual(copied.category_id.name, "Rice")
        self.assertEqual(copied.option_groups.first().options.first().name, "Full")

    def test_rerunning_a_copy_skips_everything(self):
        copy_menu(self.src, self.dst)
        second = copy_menu(self.src, self.dst)
        self.assertEqual(second["items_copied"], 0)
        self.assertEqual(second["items_skipped"], 1)
        self.assertEqual(second["categories_merged"], 1)
        self.assertEqual(FoodItem.objects.filter(restaurant=self.dst, name="Kacchi").count(), 1)

    def test_same_named_category_is_merged_not_duplicated(self):
        FoodCategory.objects.create(restaurant=self.dst, name="Rice")
        result = copy_menu(self.src, self.dst)
        self.assertEqual(result["categories_created"], 0)
        self.assertEqual(result["categories_merged"], 1)
        self.assertEqual(FoodCategory.objects.filter(restaurant=self.dst, name="Rice").count(), 1)

    def test_slug_collision_in_target_is_resolved(self):
        other_cat = FoodCategory.objects.create(restaurant=self.dst, name="Other")
        FoodItem.objects.create(restaurant=self.dst, category_id=other_cat, name="Different",
                                slug="kacchi", price=Decimal("100"))
        copy_menu(self.src, self.dst)
        copied = FoodItem.objects.get(restaurant=self.dst, name="Kacchi")
        self.assertEqual(copied.slug, "kacchi-2")

    def test_dry_run_writes_nothing(self):
        result = copy_menu(self.src, self.dst, dry_run=True)
        self.assertEqual(result["items_copied"], 1)
        self.assertFalse(FoodItem.objects.filter(restaurant=self.dst).exists())
        self.assertFalse(FoodCategory.objects.filter(restaurant=self.dst).exists())

    def test_selective_copy_into_a_chosen_category(self):
        FoodItem.objects.create(restaurant=self.src, category_id=self.cat, name="Biriyani",
                                slug="biriyani", price=Decimal("250"))
        target_cat = FoodCategory.objects.create(restaurant=self.dst, name="Specials")
        result = copy_menu(self.src, self.dst, item_ids=[self.item.id], target_category=target_cat)
        self.assertEqual(result["items_copied"], 1)
        self.assertEqual(FoodItem.objects.get(restaurant=self.dst).category_id, target_cat)
        self.assertFalse(FoodItem.objects.filter(restaurant=self.dst, name="Biriyani").exists())


class MenuCopyAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create(username="adm", email="adm@x.com", role="Admin")
        self.src = Restaurant.objects.create(name="S", slug="s", status=Restaurant.Status.ACTIVE)
        self.dst = Restaurant.objects.create(name="D", slug="d", status=Restaurant.Status.ACTIVE)
        cat = FoodCategory.objects.create(restaurant=self.src, name="Rice")
        FoodItem.objects.create(restaurant=self.src, category_id=cat, name="Kacchi",
                                slug="kacchi", price=Decimal("300"))

    def test_admin_copies_a_whole_menu(self):
        auth(self.client, self.admin)
        res = self.client.post("/api/food/admin/menu/copy/",
                               {"source_restaurant": self.src.id, "target_restaurant": self.dst.id},
                               format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["data"]["items_copied"], 1)
        self.assertTrue(FoodItem.objects.filter(restaurant=self.dst, name="Kacchi").exists())

    def test_dry_run_previews_without_writing(self):
        auth(self.client, self.admin)
        res = self.client.post("/api/food/admin/menu/copy/?dry_run=true",
                               {"source_restaurant": self.src.id, "target_restaurant": self.dst.id},
                               format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["data"]["items_copied"], 1)
        self.assertFalse(FoodItem.objects.filter(restaurant=self.dst).exists())

    def test_copying_a_restaurant_onto_itself_is_rejected(self):
        auth(self.client, self.admin)
        res = self.client.post("/api/food/admin/menu/copy/",
                               {"source_restaurant": self.src.id, "target_restaurant": self.src.id},
                               format="json")
        self.assertEqual(res.status_code, 400)

    def test_unknown_restaurant_is_rejected(self):
        auth(self.client, self.admin)
        res = self.client.post("/api/food/admin/menu/copy/",
                               {"source_restaurant": self.src.id, "target_restaurant": 99999},
                               format="json")
        self.assertEqual(res.status_code, 400)

    def test_non_admin_is_blocked(self):
        cust = User.objects.create(username="c", email="c@x.com", role="Customer")
        auth(self.client, cust)
        res = self.client.post("/api/food/admin/menu/copy/",
                               {"source_restaurant": self.src.id, "target_restaurant": self.dst.id},
                               format="json")
        self.assertEqual(res.status_code, 403)
