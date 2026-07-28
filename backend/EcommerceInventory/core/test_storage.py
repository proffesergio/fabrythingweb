import os

from django.conf import settings
from django.test import SimpleTestCase

from core.storage import save_file


class SaveFileLocalTests(SimpleTestCase):
    def test_local_save_returns_media_url_and_writes_file(self):
        url = save_file("unit_test_probe.jpg", b"\xff\xd8\xff\xdbfake", "image/jpeg")
        self.assertIn("/uploads/", url)
        name = url.rsplit("/", 1)[1]
        path = os.path.join(settings.MEDIA_ROOT, "uploads", name)
        self.assertTrue(os.path.exists(path))
        os.remove(path)
