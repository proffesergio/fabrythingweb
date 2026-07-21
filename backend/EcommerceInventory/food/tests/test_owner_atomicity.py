"""A half-created rider/restaurant must not leave an orphan User behind.

Both AdminRiderViewSet.create and services_admin.create_restaurant_with_owner
create the login User *before* the object it belongs to. Without a transaction,
any failure after that point (a DB error, a serializer reject) commits the User
anyway. The admin then retries the same form and gets a permanent
"A user with that email/username already exists." — the account is unusable and
unreachable from the UI, because no Rider/Restaurant row points at it.

This is exactly the state the production panel got stuck in.
"""
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from food.models import Rider, Restaurant

User = get_user_model()


class RiderCreateAtomicityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        admin = User.objects.create(username="atom_admin", email="atom_admin@example.com",
                                    role="Super Admin")
        token = str(RefreshToken.for_user(admin).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.payload = {
            "name": "Karim",
            "phone": "01700000000",
            "owner": {"username": "karim_rider", "email": "karim@example.com",
                      "password": "riderPass123"},
        }

    def test_failed_rider_save_rolls_back_the_user(self):
        # Simulate the production failure: the User insert succeeds, the Rider
        # insert blows up (there, a missing column from an unapplied migration).
        with mock.patch("food.views_food_ext.RiderSerializer.save",
                        side_effect=Exception("column food_rider.current_lat does not exist")):
            with self.assertRaises(Exception):
                self.client.post("/api/food/admin/riders/", self.payload, format="json")

        self.assertFalse(User.objects.filter(username="karim_rider").exists(),
                         "orphan User survived a failed rider create")
        self.assertFalse(Rider.objects.filter(name="Karim").exists())

    def test_retry_after_failure_succeeds(self):
        with mock.patch("food.views_food_ext.RiderSerializer.save",
                        side_effect=Exception("boom")):
            with self.assertRaises(Exception):
                self.client.post("/api/food/admin/riders/", self.payload, format="json")

        # The retry must not be blocked by leftovers from the failed attempt.
        res = self.client.post("/api/food/admin/riders/", self.payload, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        rider = Rider.objects.get(name="Karim")
        self.assertEqual(rider.user.username, "karim_rider")
        self.assertEqual(rider.user.role, "Rider")

    def test_invalid_rider_payload_rolls_back_the_user(self):
        # Serializer rejects the rider (name is required) after the User exists.
        res = self.client.post("/api/food/admin/riders/",
                               {"owner": self.payload["owner"]}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertFalse(User.objects.filter(username="karim_rider").exists(),
                         "orphan User survived a rejected rider payload")

    def test_created_rider_exposes_its_login_username(self):
        res = self.client.post("/api/food/admin/riders/", self.payload, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()["data"]["username"], "karim_rider")


class RestaurantCreateAtomicityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        admin = User.objects.create(username="atom_admin2", email="atom_admin2@example.com",
                                    role="Super Admin")
        token = str(RefreshToken.for_user(admin).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_failed_restaurant_save_rolls_back_the_owner(self):
        payload = {
            "name": "Kacchi Ghor",
            "owner": {"username": "kacchi_owner", "email": "kacchi@example.com",
                      "password": "ownerPass123"},
        }
        with mock.patch("food.services_admin.Restaurant.objects.create",
                        side_effect=Exception("boom")):
            with self.assertRaises(Exception):
                self.client.post("/api/food/admin/restaurants/", payload, format="json")

        self.assertFalse(User.objects.filter(username="kacchi_owner").exists(),
                         "orphan User survived a failed restaurant create")
        self.assertFalse(Restaurant.objects.filter(name="Kacchi Ghor").exists())
