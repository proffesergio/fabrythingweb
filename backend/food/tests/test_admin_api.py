from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from food.models import Restaurant

User = get_user_model()


def auth(client, user):
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


class AdminApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Users.email is unique with no default; give each test user a distinct
        # address so setUp doesn't collide on "".
        self.admin = User.objects.create(username="admin1", email="admin1@example.com", role="Super Admin")
        token = str(RefreshToken.for_user(self.admin).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.r = Restaurant.objects.create(name="Pending Co", slug="pending-co",
                                           status=Restaurant.Status.PENDING)

    def test_approve_sets_active(self):
        res = self.client.post(f"/api/food/admin/restaurants/{self.r.id}/approve/")
        self.assertEqual(res.status_code, 200)
        self.r.refresh_from_db()
        self.assertEqual(self.r.status, Restaurant.Status.ACTIVE)

    def test_suspend_sets_suspended(self):
        res = self.client.post(f"/api/food/admin/restaurants/{self.r.id}/suspend/")
        self.assertEqual(res.status_code, 200)
        self.r.refresh_from_db()
        self.assertEqual(self.r.status, Restaurant.Status.SUSPENDED)


class AdminApiSecurityTests(TestCase):
    """Task 8 security override: /api/food/ is a PUBLIC_API_PREFIXES bypass in
    core/middleware.py, so PermissionMiddleware does NOT gate these admin endpoints.
    IsAuthenticated alone would let ANY logged-in user (Customer/Rider/Restaurant)
    approve/suspend restaurants or edit zones. These tests prove IsPlatformAdmin
    actually blocks non-admin roles.
    """

    def setUp(self):
        self.client = APIClient()
        self.r = Restaurant.objects.create(name="Pending Co", slug="pending-co-2",
                                           status=Restaurant.Status.PENDING)

    def test_customer_cannot_approve_restaurant(self):
        customer = User.objects.create(username="cust1", email="cust1@example.com", role="Customer")
        auth(self.client, customer)
        res = self.client.post(f"/api/food/admin/restaurants/{self.r.id}/approve/")
        self.assertEqual(res.status_code, 403)
        self.r.refresh_from_db()
        self.assertEqual(self.r.status, Restaurant.Status.PENDING)

    def test_restaurant_vendor_cannot_approve_restaurant(self):
        vendor = User.objects.create(username="vendor1", email="vendor1@example.com", role="Restaurant")
        auth(self.client, vendor)
        res = self.client.post(f"/api/food/admin/restaurants/{self.r.id}/approve/")
        self.assertEqual(res.status_code, 403)
        self.r.refresh_from_db()
        self.assertEqual(self.r.status, Restaurant.Status.PENDING)

    def test_restaurant_vendor_cannot_create_zone(self):
        vendor = User.objects.create(username="vendor2", email="vendor2@example.com", role="Restaurant")
        auth(self.client, vendor)
        payload = {
            "name": "Hacked Zone",
            "center_lat": "23.780000",
            "center_lng": "90.270000",
            "radius_km": "5.00",
        }
        res = self.client.post("/api/food/admin/zones/", payload, format="json")
        self.assertEqual(res.status_code, 403)
