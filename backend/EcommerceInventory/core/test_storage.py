import hashlib
from unittest.mock import MagicMock, patch

from django.test import TestCase

from core.models import ImageBlob
from core.storage import save_file


class SaveFileDatabaseFallbackTests(TestCase):
    """No AWS keys configured (the test settings default) -> save_file must
    persist the bytes as a content-addressed row in the database, since
    Render's filesystem is ephemeral and a local-disk write would vanish on
    the next deploy.
    """

    def test_save_file_without_aws_keys_stores_blob_and_returns_url_with_sha256(self):
        content = b"\xff\xd8\xff\xdbfake-jpeg-bytes"
        url = save_file("probe.jpg", content, "image/jpeg")

        digest = hashlib.sha256(content).hexdigest()
        self.assertIn(digest, url)

        blob = ImageBlob.objects.get(sha256=digest)
        self.assertEqual(bytes(blob.data), content)
        self.assertEqual(blob.content_type, "image/jpeg")
        self.assertEqual(blob.byte_size, len(content))

    def test_storing_identical_bytes_twice_dedupes_to_one_row_same_url(self):
        content = b"same-bytes-twice"

        url1 = save_file("first-name.jpg", content, "image/jpeg")
        url2 = save_file("second-different-name.jpg", content, "image/jpeg")

        self.assertEqual(url1, url2)
        digest = hashlib.sha256(content).hexdigest()
        self.assertEqual(ImageBlob.objects.filter(sha256=digest).count(), 1)


class SaveFileS3PreservedTests(TestCase):
    """Existing behavior: when AWS keys ARE configured, S3 is still used and
    the DB fallback is not touched. Patches settings/keys rather than calling
    real S3.
    """

    def test_uses_s3_when_aws_keys_configured(self):
        fake_session = MagicMock()
        fake_client = MagicMock()
        fake_session.client.return_value = fake_client

        with patch("core.storage.AWS_ACCESS_KEY_ID", "real-key-id"), \
             patch("core.storage.AWS_ACESS_KEY_SECRET", "real-secret"), \
             patch("core.storage.AWS_STORAGE_BUCKET_NAME", "my-bucket"), \
             patch("core.storage.AWS_S3_REGION_NAME", "us-east-1"), \
             patch("boto3.session.Session", return_value=fake_session):
            url = save_file("photo.jpg", b"bytes", "image/jpeg")

        fake_client.put_object.assert_called_once()
        self.assertIn("my-bucket.s3.amazonaws.com", url)
        self.assertEqual(ImageBlob.objects.count(), 0)
