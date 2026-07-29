"""Shared fixtures for printing app tests."""
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from catalog.models import Products

User = get_user_model()


def auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")


def make_customer(username="cust1"):
    return User.objects.create(username=username, email=f"{username}@x.com", role="Customer")


def make_staff(username="admin1", role="Admin"):
    return User.objects.create(username=username, email=f"{username}@x.com", role=role)


def make_product(slug="tee", sku="SKU-1"):
    return Products.objects.create(
        name=slug, slug=slug, description="d", sku=sku,
        initial_buying_price=100, initial_selling_price=200, status="ACTIVE",
    )
