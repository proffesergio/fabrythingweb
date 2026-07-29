from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from catalog.models import Products, Categories

User = get_user_model()


def auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")


class AdminProductListTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create(username="admin1", email="admin1@x.com", role="Super Admin")
        self.cat = Categories.objects.create(name="Shirts", slug="shirts")

    def test_list_does_not_crash_when_product_owner_is_null(self):
        # Regression: seeded products had null domain_user_id/added_by_user_id and
        # the admin serializer dereferenced .id, 500-ing the whole list.
        Products.objects.create(name="Null Owner Tee", slug="null-owner-tee",
                                sku="FT-0001", category_id=self.cat, status="ACTIVE",
                                description="", initial_buying_price=68,
                                initial_selling_price=100)
        auth(self.client, self.admin)
        res = self.client.get("/api/products/")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertGreaterEqual(len(res.json()["data"]), 1)

    def test_seed_assigns_product_owner(self):
        from django.core.management import call_command
        User.objects.create(username="seedadmin", email="seed@x.com", role="Super Admin")
        call_command("seed_bd_store")
        self.assertGreater(Products.objects.count(), 0)
        self.assertEqual(Products.objects.filter(domain_user_id__isnull=True).count(), 0)

    def test_category_list_does_not_crash_when_owner_is_null(self):
        # Same null-owner landmine as products — the live "Categories" tab 500'd on it.
        Categories.objects.create(name="Orphan Cat", slug="orphan-cat", description="")
        auth(self.client, self.admin)
        res = self.client.get("/api/products/categories/")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertGreaterEqual(len(res.json()["data"]["data"]), 1)


class AdminProductListStockFieldsTests(TestCase):
    """The admin all-products list needs total_stock/variant_count on each
    row to render inline stock editing (single-variant products edit stock
    directly; multi-variant products need a picker) without an extra request
    per row."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create(username="stockadmin", email="stockadmin@x.com", role="Super Admin")
        self.cat = Categories.objects.create(name="Stock Cat", slug="stock-cat", description="")

    def test_list_exposes_total_stock_and_variant_count(self):
        from catalog.models import ProductVariant
        p = Products.objects.create(name="Stocked Tee", slug="stocked-tee", sku="ST-0001",
                                    category_id=self.cat, status="ACTIVE", description="",
                                    initial_buying_price=50, initial_selling_price=100)
        ProductVariant.objects.create(product=p, sku="ST-0001-A", size="S", price=100, stock_quantity=7, is_active=True)
        ProductVariant.objects.create(product=p, sku="ST-0001-B", size="M", price=100, stock_quantity=3, is_active=True)
        auth(self.client, self.admin)
        res = self.client.get("/api/products/")
        self.assertEqual(res.status_code, 200, res.content)
        row = next(r for r in res.json()["data"]["data"] if r["slug"] == "stocked-tee")
        self.assertEqual(row["total_stock"], 10)
        self.assertEqual(row["variant_count"], 2)


class ProductSourceFieldsTests(TestCase):
    def test_source_fields_default_empty(self):
        cat = Categories.objects.create(name="Laptops", slug="laptops-t", description="")
        p = Products.objects.create(
            name="X", slug="x-src", sku="FT-9001", category_id=cat,
            description="", initial_buying_price=1, initial_selling_price=2)
        self.assertEqual(p.source_url, "")
        self.assertIsNone(p.source_price)
        self.assertIsNone(p.price_synced_at)


class SeedIfEmptyGuardTests(TestCase):
    def test_seed_food_demo_if_empty_skips_when_restaurants_exist(self):
        from django.core.management import call_command
        from food.models import Restaurant
        Restaurant.objects.create(name="Real Resto", slug="real-resto")
        call_command("seed_food_demo", "--if-empty")
        # Guard prevented demo restaurants from being added.
        self.assertEqual(Restaurant.objects.count(), 1)

    def test_seed_demo_if_empty_skips_catalog_when_products_exist(self):
        from django.core.management import call_command
        cat = Categories.objects.create(name="C", slug="c", description="")
        Products.objects.create(name="Real Product", slug="real-product", sku="R-1",
                                category_id=cat, status="ACTIVE", description="",
                                initial_buying_price=10, initial_selling_price=20)
        call_command("seed_demo", "--if-empty")
        # Only the one real product remains — demo catalog was skipped.
        self.assertEqual(Products.objects.count(), 1)
