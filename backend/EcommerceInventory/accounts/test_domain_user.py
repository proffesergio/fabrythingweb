"""`domain_user_id` must never be NULL.

`core.middleware.PermissionMiddleware` and `accounts.controllers.SidebarController`
both dereference `user.domain_user_id.id` unconditionally. A NULL there is not a
missing-data inconvenience — it is an unhandled `AttributeError`, i.e. a blank
500 on `/api/getMenus/` and on every permission-gated `/api/` route, for the
whole life of that account.

`Users.save()` used to self-heal only `if not self.domain_user_id and self.id`,
and on an INSERT `self.id` is still None at that point — so every account ever
created through `create_user()` (riders and restaurant vendors are created that
way by the admin panel) was born broken and stayed broken.
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Users


class DomainUserIdTests(TestCase):
    def test_create_user_self_assigns_domain_user_id(self):
        user = Users.objects.create_user(
            username="rider1", email="rider1@example.com", password="pass12345",
            role="Rider", country="Bangladesh")

        user.refresh_from_db()
        self.assertIsNotNone(user.domain_user_id, "create_user() left domain_user_id NULL")
        self.assertEqual(user.domain_user_id_id, user.id)

    def test_explicit_domain_user_is_not_overwritten(self):
        owner = Users.objects.create_user(
            username="owner", email="owner@example.com", password="pass12345",
            role="Admin", country="Bangladesh")
        staff = Users.objects.create_user(
            username="staff", email="staff@example.com", password="pass12345",
            role="Staff", country="Bangladesh", domain_user_id=owner)

        staff.refresh_from_db()
        self.assertEqual(staff.domain_user_id_id, owner.id)

    def test_plain_create_also_self_assigns(self):
        """`objects.create()` bypasses create_user(); it must self-heal too."""
        user = Users.objects.create(
            username="plain", email="plain@example.com", password="pass12345",
            role="Customer", country="Bangladesh")

        user.refresh_from_db()
        self.assertEqual(user.domain_user_id_id, user.id)

    def test_resave_does_not_rehash_password_or_lose_domain_user(self):
        """The insert now writes twice; the second write must not double-hash."""
        user = Users.objects.create_user(
            username="pw", email="pw@example.com", password="pass12345",
            role="Customer", country="Bangladesh")

        self.assertTrue(user.check_password("pass12345"))
        user.refresh_from_db()
        self.assertTrue(user.check_password("pass12345"))
        self.assertEqual(user.domain_user_id_id, user.id)


class NullDomainUserSurvivesRequestTests(TestCase):
    """Defence in depth for rows the migration hasn't reached (or a NULL that
    sneaks in via raw SQL): a NULL domain_user_id must degrade, never 500."""

    def setUp(self):
        self.user = Users.objects.create_user(
            username="legacy", email="legacy@example.com", password="pass12345",
            role="Rider", country="Bangladesh")
        # Simulate a pre-migration row: bypass save() to force the NULL back.
        Users.objects.filter(pk=self.user.pk).update(domain_user_id=None)
        self.user.refresh_from_db()
        self.assertIsNone(self.user.domain_user_id_id)

        self.client = APIClient()
        token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_get_menus_does_not_500(self):
        """The verdict itself is environment-dependent (with no ModuleUrls rows
        seeded, PermissionMiddleware legitimately answers 400 "Module not Exist").
        What must never happen again is the unhandled AttributeError."""
        response = self.client.get("/api/getMenus/")
        self.assertNotEqual(response.status_code, 500)

    def test_permission_middleware_does_not_500(self):
        """Any gated /api/ route: middleware must fall through to its normal
        permission verdict instead of raising on the NULL."""
        response = self.client.get("/api/products/")
        self.assertNotEqual(response.status_code, 500)
