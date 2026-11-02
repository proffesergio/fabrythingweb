from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from food.models import DeviceToken

User = get_user_model()


def auth(client, user):
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


class DeviceApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.u = User.objects.create(username="c1", role="Customer")

    def test_register_requires_auth(self):
        res = self.client.post("/api/food/devices/register/",
                               {"expo_token": "ExponentPushToken[x]", "app": "customer",
                                "platform": "android"}, format="json")
        self.assertEqual(res.status_code, 401)

    def test_register_is_idempotent_upsert(self):
        auth(self.client, self.u)
        body = {"expo_token": "ExponentPushToken[x]", "app": "customer", "platform": "android"}
        self.client.post("/api/food/devices/register/", body, format="json")
        self.client.post("/api/food/devices/register/", body, format="json")
        self.assertEqual(DeviceToken.objects.filter(expo_token="ExponentPushToken[x]").count(), 1)
        d = DeviceToken.objects.get(expo_token="ExponentPushToken[x]")
        self.assertEqual(d.user, self.u)
        self.assertTrue(d.enabled)

    def test_unregister_disables(self):
        auth(self.client, self.u)
        DeviceToken.objects.create(user=self.u, expo_token="ExponentPushToken[y]",
                                   app="customer", platform="android")
        res = self.client.post("/api/food/devices/unregister/",
                               {"expo_token": "ExponentPushToken[y]"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(DeviceToken.objects.get(expo_token="ExponentPushToken[y]").enabled)
