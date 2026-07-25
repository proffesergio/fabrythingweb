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

    def test_default_sharing_on(self):
        # Customers see their rider during an active delivery by default; the
        # rider can opt out for privacy (see test_privacy_toggle).
        self.assertTrue(self.rider.is_sharing_location)
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

    def test_heartbeat_always_stores_coords_even_when_not_sharing(self):
        # The platform always tracks online riders regardless of the
        # customer-facing sharing flag, because dispatch (services_dispatch.py)
        # can only assign orders to riders with a known position.
        self.rider.is_sharing_location = False
        self.rider.save(update_fields=["is_sharing_location"])
        auth(self.client, self.u)
        self.client.post("/api/food/rider/heartbeat/", {"lat": "23.81", "lng": "90.41"}, format="json")
        self.rider.refresh_from_db()
        self.assertEqual(self.rider.current_lat, Decimal("23.810000"))
        self.assertIsNotNone(self.rider.last_seen_at)

    def test_heartbeat_stores_coords_when_sharing(self):
        auth(self.client, self.u)
        self.client.post("/api/food/rider/heartbeat/", {"lat": "23.81", "lng": "90.41"}, format="json")
        self.rider.refresh_from_db()
        self.assertEqual(self.rider.current_lat, Decimal("23.810000"))

    def test_toggling_sharing_off_does_not_clear_stored_coords(self):
        self.rider.current_lat = Decimal("23.81")
        self.rider.current_lng = Decimal("90.41")
        self.rider.save(update_fields=["current_lat", "current_lng"])
        auth(self.client, self.u)
        res = self.client.post("/api/food/rider/privacy/",
                               {"is_sharing_location": False}, format="json")
        self.assertEqual(res.status_code, 200)
        self.rider.refresh_from_db()
        self.assertFalse(self.rider.is_sharing_location)
        self.assertEqual(self.rider.current_lat, Decimal("23.810000"))
        self.assertEqual(self.rider.current_lng, Decimal("90.410000"))
