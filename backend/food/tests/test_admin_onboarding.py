from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from food.models import Restaurant, DeliveryZone, RestaurantZone, RestaurantHours

User = get_user_model()


def auth(c, u):
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(u).access_token}")


class AdminOnboardingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create(username="adm", email="adm@x.com", role="Admin")
        self.zone = DeliveryZone.objects.create(name="Z", center_lat="23.8", center_lng="90.4", radius_km="5")
        auth(self.client, self.admin)

    def test_create_restaurant_with_owner_login(self):
        payload = {
            "name": "Star Kitchen", "commission_percentage": "12.00", "base_delivery_fee": "40.00",
            "owner": {"username": "starowner", "email": "star@x.com", "phone": "0170000000", "password": "pass12345"},
            "zone_ids": [self.zone.id],
        }
        res = self.client.post("/api/food/admin/restaurants/", payload, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        r = Restaurant.objects.get(name="Star Kitchen")
        self.assertIsNotNone(r.owner)
        self.assertEqual(r.owner.role, "Restaurant")
        self.assertTrue(r.slug)
        self.assertTrue(RestaurantZone.objects.filter(restaurant=r, zone=self.zone).exists())
        # owner can authenticate against the vendor endpoint
        owner = User.objects.get(username="starowner")
        c2 = APIClient(); auth(c2, owner)
        self.assertEqual(c2.get("/api/food/vendor/restaurant/").status_code, 200)

    def test_duplicate_owner_email_rejected(self):
        User.objects.create(username="dup", email="taken@x.com", role="Customer")
        payload = {"name": "X", "owner": {"username": "newu", "email": "taken@x.com", "password": "pass12345"}}
        res = self.client.post("/api/food/admin/restaurants/", payload, format="json")
        self.assertEqual(res.status_code, 400, res.content)

    def test_create_without_owner_is_allowed(self):
        res = self.client.post("/api/food/admin/restaurants/", {"name": "No Owner"}, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertIsNone(Restaurant.objects.get(name="No Owner").owner)

    def test_assign_and_remove_zone(self):
        r = Restaurant.objects.create(name="R", slug="r")
        add = self.client.post(f"/api/food/admin/restaurants/{r.id}/zones/",
                               {"zone_id": self.zone.id, "delivery_fee": "25.00"}, format="json")
        self.assertEqual(add.status_code, 200, add.content)
        self.assertEqual(RestaurantZone.objects.get(restaurant=r, zone=self.zone).delivery_fee, Decimal("25.00"))
        rem = self.client.delete(f"/api/food/admin/restaurants/{r.id}/zones/",
                                 {"zone_id": self.zone.id}, format="json")
        self.assertEqual(rem.status_code, 200, rem.content)
        self.assertFalse(RestaurantZone.objects.filter(restaurant=r, zone=self.zone).exists())

    def test_replace_hours(self):
        r = Restaurant.objects.create(name="R", slug="r")
        payload = {"hours": [{"weekday": 0, "open_time": "09:00", "close_time": "22:00"},
                             {"weekday": 1, "open_time": "09:00", "close_time": "22:00"}]}
        res = self.client.put(f"/api/food/admin/restaurants/{r.id}/hours/", payload, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(RestaurantHours.objects.filter(restaurant=r).count(), 2)
