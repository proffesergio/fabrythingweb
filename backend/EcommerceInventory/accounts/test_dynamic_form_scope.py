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
from inventory.models import Warehouse


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


class DynamicFormCrossTenantEscalationTests(TestCase):
    """CRITICAL regression test: the platform-scope widening added for the
    category/product editor (isPlatformScope) must NOT apply to every
    dynamic-form model. isPlatformScope is true for ANY domain-root user, not
    only Super Admins, and PermissionMiddleware already lets domain-root users
    bypass the module-permission gate (core/middleware.py:58-59) -- so without
    a per-model allow-list, one tenant's domain-root Admin can fetch AND edit
    another tenant's `Users` row (e.g. flip it to role="Super Admin") or
    `Warehouse` row via /api/getForm/users/<id>/ and /api/getForm/warehouse/<id>/.

    UserController.py and WarehouseController.py still enforce the strict
    per-domain filter for their own endpoints -- the dynamic form must match
    that, for every model except category/product.
    """

    def setUp(self):
        # Tenant A: a domain-root Admin (isPlatformScope is True for them --
        # domain_user_id_id == id -- even though they are not Super Admin).
        self.tenant_a_admin = Users.objects.create_user(
            username="tenantA-admin", email="tenantA@x.com", password="x",
            role="Admin", country="Bangladesh")
        # Tenant B: a different domain-root Admin, with rows of their own.
        self.tenant_b_admin = Users.objects.create_user(
            username="tenantB-admin", email="tenantB@x.com", password="x",
            role="Admin", country="Bangladesh")
        self.tenant_b_staff = Users.objects.create_user(
            username="tenantB-staff", email="tenantB-staff@x.com", password="x",
            role="Staff", country="Bangladesh", domain_user_id=self.tenant_b_admin)
        self.tenant_b_warehouse = Warehouse.objects.create(
            name="B Warehouse", address="1 Road", city="Dhaka", state="Dhaka",
            country="Bangladesh", pincode="1200", phone="0100000000",
            email="wh@tenantb.com", additional_details={},
            domain_user_id=self.tenant_b_admin, added_by_user_id=self.tenant_b_admin)

    def _get(self, modelName, obj_id, user):
        request = APIRequestFactory().get(f"/api/getForm/{modelName}/{obj_id}/")
        force_authenticate(request, user=user)
        return DynamicFormController.as_view()(request, modelName=modelName, id=obj_id)

    def _post(self, modelName, obj_id, user, data):
        request = APIRequestFactory().post(f"/api/getForm/{modelName}/{obj_id}/", data, format="json")
        force_authenticate(request, user=user)
        return DynamicFormController.as_view()(request, modelName=modelName, id=obj_id)

    def test_domain_root_admin_cannot_fetch_foreign_tenant_users_row(self):
        res = self._get("users", self.tenant_b_staff.id, self.tenant_a_admin)
        self.assertEqual(res.status_code, 404)

    def test_domain_root_admin_cannot_escalate_foreign_tenant_users_role(self):
        res = self._post("users", self.tenant_b_staff.id, self.tenant_a_admin,
                          {"role": "Super Admin", "first_name": "x", "last_name": "x",
                           "email": self.tenant_b_staff.email, "address": "x",
                           "username": self.tenant_b_staff.username, "password": "x"})
        self.assertEqual(res.status_code, 404)
        self.tenant_b_staff.refresh_from_db()
        self.assertEqual(self.tenant_b_staff.role, "Staff",
                          "cross-tenant privilege escalation must not succeed")

    def test_domain_root_admin_cannot_fetch_foreign_tenant_warehouse_row(self):
        res = self._get("warehouse", self.tenant_b_warehouse.id, self.tenant_a_admin)
        self.assertEqual(res.status_code, 404)

    def test_domain_root_admin_cannot_edit_foreign_tenant_warehouse_row(self):
        res = self._post("warehouse", self.tenant_b_warehouse.id, self.tenant_a_admin,
                          {"name": "Hijacked", "address": "x", "city": "x", "state": "x",
                           "country": "x", "pincode": "x", "phone": "x", "email": "h@x.com",
                           "additional_details": {}, "status": "ACTIVE", "size": "SMALL",
                           "capacity": "LOW", "warehouse_type": "OWNED"})
        self.assertEqual(res.status_code, 404)
        self.tenant_b_warehouse.refresh_from_db()
        self.assertEqual(self.tenant_b_warehouse.name, "B Warehouse")

    def test_platform_scope_widening_still_works_for_category(self):
        """Must NOT regress: category is the model this widening was built
        for (see DynamicFormScopeTests above) -- a platform-scope user must
        still be able to reach a foreign-domain category row."""
        foreign_cat = Categories.objects.create(
            name="Tenant B Category", slug="tenant-b-cat", description="",
            domain_user_id=self.tenant_b_admin, added_by_user_id=self.tenant_b_admin)
        res = self._get("category", foreign_cat.id, self.tenant_a_admin)
        self.assertEqual(res.status_code, 200)
