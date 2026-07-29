"""Admin product list (GET /api/products/) browse-by-category filter.

The taxonomy is three levels deep (fashion > Men > T-shirts) and products
live in the leaves. This must reuse catalog.category_tree.descendant_category_ids
(the same helper the storefront filter uses -- see
storefront/test_category_filtering.py) rather than a second one-level
traversal, and an unrecognised category id/slug must return an empty list,
not the whole catalog.
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Users
from catalog.models import Categories, Products


def auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")


def make_product(owner, category, slug, sku):
    return Products.objects.create(
        name=slug, slug=slug, description="d", sku=sku,
        initial_buying_price=100, initial_selling_price=200,
        category_id=category, domain_user_id=owner, added_by_user_id=owner,
        status="ACTIVE",
    )


class AdminProductCategoryFilterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = Users.objects.create_user(
            username="cat-owner", email="cat-owner@x.com", password="x",
            role="Super Admin", country="Bangladesh")
        auth(self.client, self.owner)

        self.fashion = Categories.objects.create(
            name="Fashion", slug="admin-fashion", description="d",
            domain_user_id=self.owner, added_by_user_id=self.owner)
        self.men = Categories.objects.create(
            name="Men", slug="admin-fashion-men", description="d", parent_id=self.fashion,
            domain_user_id=self.owner, added_by_user_id=self.owner)
        self.tshirts = Categories.objects.create(
            name="T-shirts", slug="admin-men-tshirts", description="d", parent_id=self.men,
            domain_user_id=self.owner, added_by_user_id=self.owner)
        self.leaf_product = make_product(self.owner, self.tshirts, "admin-leaf-tee", "ADM-LEAF-1")

        self.other = Categories.objects.create(
            name="Phones", slug="admin-phones", description="d",
            domain_user_id=self.owner, added_by_user_id=self.owner)
        make_product(self.owner, self.other, "admin-phone-1", "ADM-PHONE-1")

    def test_filter_by_root_category_slug_returns_grandchild_leaf_product(self):
        res = self.client.get("/api/products/?category=admin-fashion")
        self.assertEqual(res.status_code, 200, res.content)
        slugs = [r["slug"] for r in res.json()["data"]["data"]]
        self.assertIn("admin-leaf-tee", slugs)
        self.assertNotIn("admin-phone-1", slugs)

    def test_filter_by_root_category_id_returns_grandchild_leaf_product(self):
        res = self.client.get(f"/api/products/?category={self.fashion.id}")
        self.assertEqual(res.status_code, 200, res.content)
        slugs = [r["slug"] for r in res.json()["data"]["data"]]
        self.assertIn("admin-leaf-tee", slugs)
        self.assertNotIn("admin-phone-1", slugs)

    def test_filter_by_leaf_category_returns_only_its_own_products(self):
        res = self.client.get(f"/api/products/?category={self.tshirts.slug}")
        self.assertEqual(res.status_code, 200, res.content)
        slugs = [r["slug"] for r in res.json()["data"]["data"]]
        self.assertEqual(slugs, ["admin-leaf-tee"])

    def test_unknown_category_returns_empty_not_entire_catalog(self):
        res = self.client.get("/api/products/?category=does-not-exist-admin")
        self.assertEqual(res.status_code, 200, res.content)
        rows = res.json()["data"]["data"]
        self.assertEqual(rows, [])

    def test_no_category_param_returns_everything(self):
        res = self.client.get("/api/products/")
        self.assertEqual(res.status_code, 200, res.content)
        slugs = [r["slug"] for r in res.json()["data"]["data"]]
        self.assertIn("admin-leaf-tee", slugs)
        self.assertIn("admin-phone-1", slugs)


class AdminCategoryListReturnsFullTreeTests(TestCase):
    """The category dropdown feeding the admin filter must expose parents AND
    children -- products sit in leaf categories, so a flat list of roots
    alone would give the UI nowhere to filter by the leaves."""

    def setUp(self):
        self.client = APIClient()
        self.owner = Users.objects.create_user(
            username="cat-tree-owner", email="cat-tree-owner@x.com", password="x",
            role="Super Admin", country="Bangladesh")
        auth(self.client, self.owner)
        self.fashion = Categories.objects.create(
            name="Fashion", slug="tree-fashion", description="d",
            domain_user_id=self.owner, added_by_user_id=self.owner)
        self.men = Categories.objects.create(
            name="Men", slug="tree-fashion-men", description="d", parent_id=self.fashion,
            domain_user_id=self.owner, added_by_user_id=self.owner)
        Categories.objects.create(
            name="T-shirts", slug="tree-men-tshirts", description="d", parent_id=self.men,
            domain_user_id=self.owner, added_by_user_id=self.owner)

    def test_category_list_nests_grandchildren(self):
        res = self.client.get("/api/products/categories/")
        self.assertEqual(res.status_code, 200, res.content)
        rows = res.json()["data"]["data"]
        fashion_row = next(r for r in rows if r["slug"] == "tree-fashion")
        self.assertEqual(len(fashion_row["children"]), 1)
        men_row = fashion_row["children"][0]
        self.assertEqual(men_row["slug"], "tree-fashion-men")
        self.assertEqual(len(men_row["children"]), 1)
        self.assertEqual(men_row["children"][0]["slug"], "tree-men-tshirts")
