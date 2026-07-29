"""IMPORTANT 2: DynamicFormController.post() returns the saved instance via
Django's raw `serialize('json', [model_instace])`, which bypasses
`absolutize_media_url` entirely (it emits the stored field value verbatim).
`getDynamicFormModels()` routes both 'product' and 'category' through this
controller, so right after an admin saves either one, the POST response can
carry a bare `/api/media/<hash>/` path -- it only self-corrects on the next
list refetch, which goes through ProductController/CategoryController and
already calls absolutize_image_list.

This pins that the POST response absolutizes `image` the same way.
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Users
from catalog.models import Products


def auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")


# Products._meta has many non-null fields, and DynamicFormController's
# missing-fields check applies on update too (it doesn't distinguish create
# vs. update) -- every key below must be present in the POST body.
PRODUCT_UPDATE_BODY = {
    "name": "Updated Product Name",
    "slug": "updated-product-name",
    "image": ["/api/media/realhash1234/"],
    "description": "d",
    "specifications": {},
    "html_description": "",
    "highlights": [],
    "sku": "FAB-9001",
    "initial_buying_price": 100,
    "initial_selling_price": 200,
    "dimensions": "0x0x0",
    "uom": "PCS",
    "color": "",
    "tax_percentage": 0,
    "brand": "",
    "brand_model": "",
    "status": "ACTIVE",
    "gender": "UNISEX",
    "available_sizes": [],
    "size_chart": {},
    "material": "",
    "seo_title": "",
    "seo_description": "",
    "seo_keywords": [],
    "source_url": "",
    "addition_details": {},
}


class DynamicFormImageAbsolutizationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = Users.objects.create_user(
            username="imgadmin", email="imgadmin@x.com", password="x",
            role="Super Admin", country="Bangladesh")
        self.product = Products.objects.create(
            name="Original Product", slug="original-product",
            description="d", sku="FAB-1000",
            initial_buying_price=100, initial_selling_price=200,
            image=["/api/media/realhash1234/"],
            domain_user_id=self.admin, added_by_user_id=self.admin, status="ACTIVE",
        )

    def test_post_response_absolutizes_a_stored_relative_image_url(self):
        auth(self.client, self.admin)
        res = self.client.post(
            f"/api/getForm/product/{self.product.id}/", PRODUCT_UPDATE_BODY, format="json")

        self.assertEqual(res.status_code, 200, res.content)
        image = res.json()["data"]["image"]
        self.assertIsInstance(image, list)
        self.assertTrue(
            image[0].startswith("http://testserver/api/media/realhash1234/"),
            f"expected an absolute URL, got {image[0]!r}")
