"""`GET /api/media/<sha256>/` — public, content-addressed image serving.

This is the read side of the DB-backed image storage added in
core/storage.py: when there are no S3 keys, save_file() stores the bytes as
an ImageBlob row instead of the (ephemeral, Render-wiped) local disk, and
this view is how a browser <img src> actually gets those bytes back.

Exercised through self.client (not the view function directly) because the
project's PermissionMiddleware gates everything under /api/ behind a JWT
unless the path is in PUBLIC_API_PREFIXES — a direct view-function call would
never see that middleware and could pass while the real endpoint 401s.
"""

from django.test import TestCase

from core.models import ImageBlob


class MediaBlobViewTests(TestCase):
    def setUp(self):
        self.content = b"\xff\xd8\xff\xdbsome-jpeg-bytes"
        self.blob = ImageBlob.objects.create(
            sha256="a" * 64,
            content_type="image/jpeg",
            data=self.content,
            byte_size=len(self.content),
        )
        # Overwrite with a real digest-shaped value derived from content so
        # tests read naturally; sha256 uniqueness/format isn't otherwise
        # enforced by the DB in sqlite.
        import hashlib
        self.digest = hashlib.sha256(self.content).hexdigest()
        self.blob.sha256 = self.digest
        self.blob.save()

    def test_returns_200_exact_bytes_and_content_type(self):
        response = self.client.get(f"/api/media/{self.digest}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, self.content)
        self.assertEqual(response["Content-Type"], "image/jpeg")

    def test_public_without_authentication(self):
        """Exercised through the test client so PermissionMiddleware actually
        runs -- this is the trap a direct view-function call would miss.
        """
        response = self.client.get(f"/api/media/{self.digest}/")
        self.assertNotEqual(response.status_code, 401)
        self.assertNotEqual(response.status_code, 400)
        self.assertEqual(response.status_code, 200)

    def test_sets_immutable_cache_control_and_etag(self):
        response = self.client.get(f"/api/media/{self.digest}/")
        self.assertEqual(response["ETag"], self.digest)
        self.assertEqual(
            response["Cache-Control"], "public, max-age=31536000, immutable"
        )

    def test_if_none_match_returns_304(self):
        response = self.client.get(
            f"/api/media/{self.digest}/", HTTP_IF_NONE_MATCH=self.digest
        )
        self.assertEqual(response.status_code, 304)

    def test_unknown_hash_returns_404(self):
        response = self.client.get(f"/api/media/{'0' * 64}/")
        self.assertEqual(response.status_code, 404)
