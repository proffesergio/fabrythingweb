from django.test import TestCase
from rest_framework.test import APIClient


class MobileConfigTests(TestCase):
    def test_public_and_shape(self):
        res = APIClient().get("/api/food/mobile/config/")
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertIn("customer", data["min_supported_version"])
        self.assertEqual(data["support"]["facebook_url"], "https://www.facebook.com/fabrything")
        self.assertIn("tile_url", data)
