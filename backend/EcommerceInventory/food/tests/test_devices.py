from django.test import TestCase
from django.contrib.auth import get_user_model
from food.models import DeviceToken

User = get_user_model()


class DeviceTokenModelTests(TestCase):
    def test_create_and_str(self):
        u = User.objects.create(username="c1", role="Customer")
        d = DeviceToken.objects.create(
            user=u, expo_token="ExponentPushToken[abc]",
            app=DeviceToken.App.CUSTOMER, platform=DeviceToken.Platform.ANDROID,
        )
        self.assertTrue(d.enabled)
        self.assertIn("abc", str(d))

    def test_expo_token_unique(self):
        u = User.objects.create(username="c2", role="Customer")
        DeviceToken.objects.create(user=u, expo_token="ExponentPushToken[dup]",
                                   app=DeviceToken.App.CUSTOMER, platform=DeviceToken.Platform.IOS)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            DeviceToken.objects.create(user=u, expo_token="ExponentPushToken[dup]",
                                       app=DeviceToken.App.RIDER, platform=DeviceToken.Platform.IOS)
