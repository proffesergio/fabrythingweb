"""MINOR 3: absolutize_media_url / absolutize_image_list must not crash on a
non-string entry in the `image` JSONField. A legacy row can carry a stray
non-string value (e.g. a dict or int) there; `.startswith(...)` on it would
500 the whole response. `purge_demo_catalog._is_demo_image` already guards
this the same way (`isinstance(url, str) and ...`) -- match it here too.

The one thing that must NOT change: a missing `request` context still raises
for a genuinely relative string URL -- that guardrail is deliberate (see the
docstring on absolutize_media_url) and is pinned below so it doesn't quietly
regress while fixing the non-string case.
"""
from django.test import RequestFactory, TestCase

from core.helpers import absolutize_image_list, absolutize_media_url


class AbsolutizeMediaUrlMalformedInputTests(TestCase):
    def setUp(self):
        self.request = RequestFactory().get("/")

    def test_non_string_single_value_is_returned_unchanged_not_raised(self):
        self.assertEqual(absolutize_media_url(123, self.request), 123)
        self.assertEqual(absolutize_media_url({"not": "a url"}, self.request), {"not": "a url"})

    def test_image_list_with_non_string_entries_does_not_crash(self):
        images = ["/api/media/realhash/", 123, None, {"not": "a url"}, "https://already-absolute.example/x.jpg"]
        result = absolutize_image_list(images, self.request)
        self.assertTrue(result[0].startswith("http://testserver/api/media/realhash/"))
        self.assertEqual(result[1], 123)
        self.assertIsNone(result[2])
        self.assertEqual(result[3], {"not": "a url"})
        self.assertEqual(result[4], "https://already-absolute.example/x.jpg")

    def test_missing_request_still_raises_for_a_relative_string_url(self):
        """The deliberate guardrail: a missing request context is a bug in the
        calling serializer, not something to paper over -- it must keep
        raising. Only the non-string-value case should degrade quietly."""
        with self.assertRaises(ValueError):
            absolutize_media_url("/api/media/realhash/", None)
