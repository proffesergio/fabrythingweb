from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from food.models import Rider

User = get_user_model()


def auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(user).access_token)}")


class RiderPrivacyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.u = User.objects.create(username="r1", role="Rider")
        self.rider = Rider.objects.create(user=self.u, name="R1")

    def test_default_not_sharing(self):
        self.assertFalse(self.rider.is_sharing_location)
        self.assertTrue(self.rider.nav_display_enabled)

    def test_privacy_toggle(self):
        auth(self.client, self.u)
        res = self.client.post("/api/food/rider/privacy/",
                               {"is_sharing_location": True, "nav_display_enabled": False},
                               format="json")
        self.assertEqual(res.status_code, 200)
        self.rider.refresh_from_db()
        self.assertTrue(self.rider.is_sharing_location)
        self.assertFalse(self.rider.nav_display_enabled)

    def test_heartbeat_ignores_coords_when_not_sharing(self):
        auth(self.client, self.u)
        self.client.post("/api/food/rider/heartbeat/", {"lat": "23.81", "lng": "90.41"}, format="json")
        self.rider.refresh_from_db()
        self.assertIsNone(self.rider.current_lat)
        self.assertIsNotNone(self.rider.last_seen_at)

    def test_heartbeat_stores_coords_when_sharing(self):
        self.rider.is_sharing_location = True
        self.rider.save(update_fields=["is_sharing_location"])
        auth(self.client, self.u)
        self.client.post("/api/food/rider/heartbeat/", {"lat": "23.81", "lng": "90.41"}, format="json")
        self.rider.refresh_from_db()
        self.assertEqual(self.rider.current_lat, Decimal("23.810000"))
