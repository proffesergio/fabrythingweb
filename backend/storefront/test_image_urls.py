"""
BUG 1: product/category images are stored as relative paths.

``core.storage.save_file`` returns a *relative* ``/api/media/<sha256>/`` path
when the DB-blob fallback is used (no S3 keys configured), and that path is
stored verbatim in ``Products.image`` / ``Categories.image``. The storefront
lives on a different origin (fabrything.com) than the API
(fabrythingweb.onrender.com), so a relative path in an ``<img src>`` 404s.

These tests pin that every client-facing serializer absolutizes the path
using the request in context, while leaving already-absolute URLs (partner
source images) untouched.
"""
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Users
from catalog.models import Categories, Products


class ImageAbsolutizationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = Users.objects.create_user(
            username="owner", email="owner@x.com", password="x",
            role="Super Admin", country="Bangladesh")
        self.category = Categories.objects.create(
            name="T-shirts", slug="men-tshirts", description="tees",
            image=["/api/media/deadbeef1234/"],
            domain_user_id=self.owner, added_by_user_id=self.owner,
        )
        self.relative_product = Products.objects.create(
            name="Relative Image Tee", slug="relative-image-tee",
            description="a tee", sku="SKU-REL-1",
            initial_buying_price=100, initial_selling_price=200,
            image=["/api/media/abc123hash/"],
            category_id=self.category, domain_user_id=self.owner,
            added_by_user_id=self.owner, status="ACTIVE",
        )
        self.absolute_product = Products.objects.create(
            name="Absolute Image Tee", slug="absolute-image-tee",
            description="a tee", sku="SKU-ABS-1",
            initial_buying_price=100, initial_selling_price=200,
            image=["https://partner-store.com/img/tee.jpg"],
            category_id=self.category, domain_user_id=self.owner,
            added_by_user_id=self.owner, status="ACTIVE",
        )

    def test_product_list_absolutizes_relative_media_path(self):
        res = self.client.get("/api/store/products/")
        self.assertEqual(res.status_code, 200, res.content)
        rows = res.json()["data"]["data"]
        row = next(r for r in rows if r["slug"] == "relative-image-tee")
        self.assertEqual(row["image"], ["http://testserver/api/media/abc123hash/"])

    def test_product_list_leaves_absolute_url_untouched(self):
        res = self.client.get("/api/store/products/")
        rows = res.json()["data"]["data"]
        row = next(r for r in rows if r["slug"] == "absolute-image-tee")
        self.assertEqual(row["image"], ["https://partner-store.com/img/tee.jpg"])

    def test_product_detail_absolutizes_relative_media_path(self):
        res = self.client.get("/api/store/products/relative-image-tee/")
        self.assertEqual(res.status_code, 200, res.content)
        data = res.json()["data"]
        self.assertEqual(data["image"], ["http://testserver/api/media/abc123hash/"])

    def test_category_list_absolutizes_relative_media_path(self):
        Categories.objects.filter(pk=self.category.pk).update(parent_id=None)
        res = self.client.get("/api/store/categories/")
        self.assertEqual(res.status_code, 200, res.content)
        rows = res.json()["data"]
        row = next(r for r in rows if r["slug"] == "men-tshirts")
        self.assertEqual(row["image"], ["http://testserver/api/media/deadbeef1234/"])

    def test_homepage_absolutizes_relative_media_path(self):
        res = self.client.get("/api/store/homepage/")
        self.assertEqual(res.status_code, 200, res.content)
        arrivals = res.json()["data"]["new_arrivals"]
        row = next(r for r in arrivals if r["slug"] == "relative-image-tee")
        self.assertEqual(row["image"], ["http://testserver/api/media/abc123hash/"])
