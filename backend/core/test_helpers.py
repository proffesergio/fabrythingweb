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

from accounts.models import Users
from core.helpers import absolutize_image_list, absolutize_media_url, isPlatformScope, isPlatformStaff


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


class IsPlatformStaffTests(TestCase):
    """isPlatformScope alone is TRUE for any domain-root user -- and
    Users.save() self-assigns domain_user_id = self.id for every account
    created without one, so a plain self-signed-up Customer/Rider/Restaurant
    is their own domain root too. isPlatformStaff is the canonical
    authorization predicate: a back-office role (Admin/Super Admin/Staff)
    that is ALSO platform-scoped."""

    def test_self_signed_up_customer_is_platform_scope_but_not_platform_staff(self):
        customer = Users.objects.create_user(
            username="isp-customer", email="isp-customer@x.com", password="x",
            role="Customer", country="Bangladesh")
        # The trap this whole fix exists for: isPlatformScope alone is True.
        self.assertTrue(isPlatformScope(customer))
        self.assertFalse(isPlatformStaff(customer))

    def test_self_signed_up_rider_is_not_platform_staff(self):
        rider = Users.objects.create_user(
            username="isp-rider", email="isp-rider@x.com", password="x",
            role="Rider", country="Bangladesh")
        self.assertTrue(isPlatformScope(rider))
        self.assertFalse(isPlatformStaff(rider))

    def test_self_signed_up_restaurant_is_not_platform_staff(self):
        restaurant = Users.objects.create_user(
            username="isp-restaurant", email="isp-restaurant@x.com", password="x",
            role="Restaurant", country="Bangladesh")
        self.assertTrue(isPlatformScope(restaurant))
        self.assertFalse(isPlatformStaff(restaurant))

    def test_super_admin_is_platform_staff(self):
        super_admin = Users.objects.create_user(
            username="isp-super", email="isp-super@x.com", password="x",
            role="Super Admin", country="Bangladesh")
        self.assertTrue(isPlatformStaff(super_admin))

    def test_domain_root_admin_is_platform_staff(self):
        admin = Users.objects.create_user(
            username="isp-admin", email="isp-admin@x.com", password="x",
            role="Admin", country="Bangladesh")
        self.assertTrue(isPlatformStaff(admin))

    def test_domain_root_staff_is_platform_staff(self):
        staff = Users.objects.create_user(
            username="isp-staff-root", email="isp-staff-root@x.com", password="x",
            role="Staff", country="Bangladesh")
        self.assertTrue(isPlatformStaff(staff))

    def test_sub_domain_staff_is_not_platform_staff(self):
        owner = Users.objects.create_user(
            username="isp-owner", email="isp-owner@x.com", password="x",
            role="Super Admin", country="Bangladesh")
        sub_staff = Users.objects.create_user(
            username="isp-sub-staff", email="isp-sub-staff@x.com", password="x",
            role="Staff", country="Bangladesh", domain_user_id=owner)
        self.assertFalse(isPlatformScope(sub_staff))
        self.assertFalse(isPlatformStaff(sub_staff))
