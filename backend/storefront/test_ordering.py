"""Production 500: GET /api/store/products/?ordering=newest crashed every
storefront category page.

PublicProductListView.get_queryset() already maps the friendly `ordering`
query param (`newest`, `price_low`, `price_high`, `name`) to a real model
field / `-field` and orders the queryset with it. But
CommonListAPIMixin.common_list_decorator then re-reads the SAME raw query
param and calls queryset.order_by(ordering) again with the raw string --
`'newest'` is not a column on Products, so Django raises FieldError, which
surfaces to the client as a bare 500. `ordering=name` happened to survive
only because `name` is coincidentally a real column.

The storefront frontend (ProductCatalog.js) defaults every request to
`ordering=newest`, so this took down the entire shop page.

Fix: the decorator must validate the raw ordering value before calling
order_by() and silently ignore anything that isn't a real field/annotation
on the queryset's model, leaving the view's own ordering (set in
get_queryset) intact instead of raising.
"""
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Users
from catalog.models import Categories, Products


def make_product(owner, category, slug, sku, price, name=None):
    return Products.objects.create(
        name=name or slug, slug=slug, description="d", sku=sku,
        initial_buying_price=price, initial_selling_price=price,
        category_id=category, domain_user_id=owner, added_by_user_id=owner,
        status="ACTIVE",
    )


class StorefrontOrderingDoesNotCrashTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = Users.objects.create_user(
            username="ord-owner", email="ord-owner@x.com", password="x",
            role="Super Admin", country="Bangladesh")
        self.category = Categories.objects.create(
            name="Computers", slug="computers", description="d",
            domain_user_id=self.owner, added_by_user_id=self.owner)
        self.cheap = make_product(self.owner, self.category, "cheap-item", "SKU-CHEAP", 100, name="Alpha")
        self.expensive = make_product(self.owner, self.category, "expensive-item", "SKU-EXP", 900, name="Zulu")

    def test_ordering_newest_returns_200_with_products(self):
        """This is the exact production failure: every shop page load and
        every category click defaults to ordering=newest."""
        res = self.client.get("/api/store/products/?page=1&pageSize=12&ordering=newest")
        self.assertEqual(res.status_code, 200, res.content)
        rows = res.json()["data"]["data"]
        self.assertEqual(len(rows), 2)

    def test_ordering_newest_with_category_returns_200(self):
        res = self.client.get("/api/store/products/?category=computers&ordering=newest")
        self.assertEqual(res.status_code, 200, res.content)

    def test_ordering_price_low_sorts_ascending(self):
        res = self.client.get("/api/store/products/?ordering=price_low")
        self.assertEqual(res.status_code, 200, res.content)
        slugs = [r["slug"] for r in res.json()["data"]["data"]]
        self.assertEqual(slugs, ["cheap-item", "expensive-item"])

    def test_ordering_price_high_sorts_descending(self):
        res = self.client.get("/api/store/products/?ordering=price_high")
        self.assertEqual(res.status_code, 200, res.content)
        slugs = [r["slug"] for r in res.json()["data"]["data"]]
        self.assertEqual(slugs, ["expensive-item", "cheap-item"])

    def test_ordering_name_sorts_alphabetically(self):
        res = self.client.get("/api/store/products/?ordering=name")
        self.assertEqual(res.status_code, 200, res.content)
        names = [r["name"] for r in res.json()["data"]["data"]]
        self.assertEqual(names, ["Alpha", "Zulu"])

    def test_ordering_garbage_field_does_not_500(self):
        res = self.client.get("/api/store/products/?ordering=nonexistent_field")
        self.assertEqual(res.status_code, 200, res.content)

    def test_ordering_sql_injection_attempt_does_not_500(self):
        res = self.client.get("/api/store/products/?ordering=;DROP TABLE catalog_products;")
        self.assertEqual(res.status_code, 200, res.content)
