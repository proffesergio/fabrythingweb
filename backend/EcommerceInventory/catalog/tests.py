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
