"""Platform-scope rule for the dynamic form editor.

The admin LIST views (ProductListView/CategoryListView) already show every row
to Super Admins and domain-root users, but DynamicFormController filtered the
edit target by exact domain match — so seeded categories (owned by the first
Super Admin) listed fine and 404'd on edit ("Model Item Not Found").
"""
from django.test import TestCase
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Users
from accounts.controllers.DynamicFormController import DynamicFormController
from catalog.models import Categories


def auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")


class DynamicFormScopeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # seeder: first Super Admin — owns the seeded rows
        self.seeder = Users.objects.create_user(
            username="seedadmin", email="seed@x.com", password="x",
            role="Super Admin", country="Bangladesh")
        # the admin actually using the panel — a *different* domain root
        self.admin = Users.objects.create_user(
            username="fadmin", email="fadmin@x.com", password="x",
            role="Admin", country="Bangladesh")
        # a staff user inside the seeder's domain (non-root)
        self.staff = Users.objects.create_user(
            username="staff1", email="staff1@x.com", password="x",
            role="Staff", country="Bangladesh", domain_user_id=self.seeder)
        self.seeded_cat = Categories.objects.create(
            name="Men's Fashion", slug="mens-fashion", description="seeded",
            domain_user_id=self.seeder, added_by_user_id=self.seeder)
        self.orphan_cat = Categories.objects.create(
            name="Orphan", slug="orphan-cat", description="null owner")
        Categories.objects.filter(pk=self.orphan_cat.pk).update(domain_user_id=None)

    def test_admin_can_fetch_edit_form_for_foreign_owned_row(self):
        auth(self.client, self.admin)
        res = self.client.get(f"/api/getForm/category/{self.seeded_cat.id}/")
        self.assertEqual(res.status_code, 200, res.content)

    def test_admin_can_fetch_edit_form_for_null_domain_row(self):
        auth(self.client, self.admin)
        res = self.client.get(f"/api/getForm/category/{self.orphan_cat.id}/")
        self.assertEqual(res.status_code, 200, res.content)

    def test_admin_update_preserves_original_owner(self):
        auth(self.client, self.admin)
        res = self.client.post(
            f"/api/getForm/category/{self.seeded_cat.id}/",
            {"name": "Men", "description": "renamed", "slug": "mens-fashion", "display_order": 0}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.seeded_cat.refresh_from_db()
        self.assertEqual(self.seeded_cat.name, "Men")
        self.assertEqual(self.seeded_cat.domain_user_id_id, self.seeder.id,
                         "update must not re-own the row to the editor")

    def test_non_root_staff_blocked_by_permission_middleware(self):
        # Non-domain-root users (staff) are blocked by PermissionMiddleware
        # (core.middleware.PermissionMiddleware) before reaching DynamicFormController.
        # They are denied at the middleware layer because they are not Super Admin
        # or domain-root, and there is no ModuleUrls permission entry for /api/getForm/.
        # This prevents a cross-domain request from ever reaching the controller.
        foreign = Categories.objects.create(
            name="Foreign", slug="foreign-cat", description="",
            domain_user_id=self.admin, added_by_user_id=self.admin)
        auth(self.client, self.staff)
        res = self.client.get(f"/api/getForm/category/{foreign.id}/")
        # Middleware blocks non-domain-root users with 400 "Module not Exist"
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["message"], "Module not Exist")

    def test_controller_denies_cross_tenant_row_for_non_root_user(self):
        """The middleware gates /api/getForm/ for non-root users, but it runs the
        view before deciding (core/middleware.py:50) — so the controller's own
        domain filter is the real last line of defense. Test it directly."""
        foreign = Categories.objects.create(
            name="Foreign Direct", slug="foreign-direct", description="",
            domain_user_id=self.admin, added_by_user_id=self.admin)
        request = APIRequestFactory().get(f"/api/getForm/category/{foreign.id}/")
        force_authenticate(request, user=self.staff)
        res = DynamicFormController.as_view()(request, modelName="category", id=foreign.id)
        self.assertEqual(res.status_code, 404)

    def test_controller_allows_own_domain_row_for_non_root_user(self):
        """Same path, but the row is inside the staff user's own domain — proves
        the 404 above comes from the domain filter, not from blanket denial."""
        mine = Categories.objects.create(
            name="Seeder Row", slug="seeder-row", description="",
            domain_user_id=self.seeder, added_by_user_id=self.seeder)
        request = APIRequestFactory().get(f"/api/getForm/category/{mine.id}/")
        force_authenticate(request, user=self.staff)
        res = DynamicFormController.as_view()(request, modelName="category", id=mine.id)
        self.assertEqual(res.status_code, 200)

    def test_own_domain_row_still_editable(self):
        mine = Categories.objects.create(
            name="Mine", slug="mine-cat", description="",
            domain_user_id=self.admin, added_by_user_id=self.admin)
        auth(self.client, self.admin)
        res = self.client.get(f"/api/getForm/category/{mine.id}/")
        self.assertEqual(res.status_code, 200, res.content)

    def test_create_still_assigns_owner(self):
        auth(self.client, self.admin)
        res = self.client.post(
            "/api/getForm/category/",
            {"name": "New Cat", "description": "d", "display_order": 0, "slug": "new-cat"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        cat = Categories.objects.get(slug="new-cat")
        self.assertEqual(cat.domain_user_id_id, self.admin.domain_user_id_id)
