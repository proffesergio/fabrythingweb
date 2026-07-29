"""
BUG 2: category filtering (and product_count) only descend ONE level.

The taxonomy is three deep (``fashion > Men > T-shirts``); products live in
the leaves. ``PublicProductListView.get_queryset`` and
``StorefrontCategorySerializer.get_product_count`` both only collected the
direct children of the requested category, so filtering by ``fashion``
missed every grandchild (T-shirts, Polos, ...) and the displayed counts were
wrong in the same way.

BUG 3 (unknown slug returns the whole catalog) is pinned alongside it since
it lives in the same code block.
"""
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Users
from catalog.category_tree import descendant_category_ids
from catalog.models import Categories, Products


def make_product(owner, category, slug, sku):
    return Products.objects.create(
        name=slug, slug=slug, description="d", sku=sku,
        initial_buying_price=100, initial_selling_price=200,
        category_id=category, domain_user_id=owner, added_by_user_id=owner,
        status="ACTIVE",
    )


class ThreeLevelCategoryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = Users.objects.create_user(
            username="owner2", email="owner2@x.com", password="x",
            role="Super Admin", country="Bangladesh")
        self.fashion = Categories.objects.create(
            name="Fashion", slug="fashion", description="d",
            domain_user_id=self.owner, added_by_user_id=self.owner)
        self.men = Categories.objects.create(
            name="Men", slug="fashion-men", description="d", parent_id=self.fashion,
            domain_user_id=self.owner, added_by_user_id=self.owner)
        self.tshirts = Categories.objects.create(
            name="T-shirts", slug="men-tshirts", description="d", parent_id=self.men,
            domain_user_id=self.owner, added_by_user_id=self.owner)
        self.leaf_product = make_product(self.owner, self.tshirts, "leaf-tee", "SKU-LEAF-1")

        # An unrelated top-level category + product must never show up.
        self.other = Categories.objects.create(
            name="Phones", slug="phones", description="d",
            domain_user_id=self.owner, added_by_user_id=self.owner)
        make_product(self.owner, self.other, "phone-1", "SKU-PHONE-1")

    def test_filtering_by_root_returns_grandchild_leaf_product(self):
        res = self.client.get("/api/store/products/?category=fashion")
        self.assertEqual(res.status_code, 200, res.content)
        slugs = [r["slug"] for r in res.json()["data"]["data"]]
        self.assertIn("leaf-tee", slugs)
        self.assertNotIn("phone-1", slugs)

    def test_product_count_on_root_counts_grandchild_leaf(self):
        res = self.client.get("/api/store/categories/")
        self.assertEqual(res.status_code, 200, res.content)
        rows = res.json()["data"]
        fashion_row = next(r for r in rows if r["slug"] == "fashion")
        self.assertEqual(fashion_row["product_count"], 1)

    def test_unknown_category_slug_returns_empty_not_entire_catalog(self):
        res = self.client.get("/api/store/products/?category=does-not-exist")
        self.assertEqual(res.status_code, 200, res.content)
        rows = res.json()["data"]["data"]
        self.assertEqual(rows, [])

    def test_descendant_category_ids_terminates_on_cyclic_parent(self):
        # A self-referencing / cyclic parent_id must not hang the site.
        a = Categories.objects.create(
            name="A", slug="cycle-a", description="d",
            domain_user_id=self.owner, added_by_user_id=self.owner)
        b = Categories.objects.create(
            name="B", slug="cycle-b", description="d", parent_id=a,
            domain_user_id=self.owner, added_by_user_id=self.owner)
        a.parent_id = b
        a.save()

        ids = descendant_category_ids(a)
        self.assertEqual(set(ids), {a.id, b.id})
