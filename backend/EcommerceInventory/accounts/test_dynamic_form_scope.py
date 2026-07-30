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
from catalog.models import Categories, Products
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


class DynamicFormNonStaffRoleEscalationTests(TestCase):
    """CRITICAL regression test, the same bug as
    DynamicFormCrossTenantEscalationTests above but for the *role* axis
    instead of the tenant axis: core.helpers.isPlatformScope is true for ANY
    domain-root user, and Users.save() self-assigns domain_user_id = self.id
    for every account created without one -- so a plain self-signed-up
    Customer (or Rider, or Restaurant) is their own domain root too, even
    though the product/category widening (PLATFORM_SCOPE_WIDENED_MODELS) was
    only ever meant for back-office roles. Before the fix this let a Customer
    fetch AND edit ANY product/category belonging to ANY tenant via
    /api/getForm/product/<id>/ and /api/getForm/category/<id>/ -- a full
    cross-domain privilege escalation reachable by anyone who can sign up."""

    def setUp(self):
        self.owner = Users.objects.create_user(
            username="store-owner", email="store-owner@x.com", password="x",
            role="Admin", country="Bangladesh")
        self.customer = Users.objects.create_user(
            username="plain-customer", email="plain-customer@x.com", password="x",
            role="Customer", country="Bangladesh")
        self.rider = Users.objects.create_user(
            username="plain-rider", email="plain-rider@x.com", password="x",
            role="Rider", country="Bangladesh")
        self.restaurant = Users.objects.create_user(
            username="plain-restaurant", email="plain-restaurant@x.com", password="x",
            role="Restaurant", country="Bangladesh")
        # Each is its own domain root, exactly like isPlatformScope's trap.
        for u in (self.customer, self.rider, self.restaurant):
            self.assertEqual(u.domain_user_id_id, u.id)

        self.category = Categories.objects.create(
            name="Store Category", slug="store-category", description="",
            domain_user_id=self.owner, added_by_user_id=self.owner)

    def _get(self, modelName, obj_id, user):
        request = APIRequestFactory().get(f"/api/getForm/{modelName}/{obj_id}/")
        force_authenticate(request, user=user)
        return DynamicFormController.as_view()(request, modelName=modelName, id=obj_id)

    def _post(self, modelName, obj_id, user, data):
        request = APIRequestFactory().post(f"/api/getForm/{modelName}/{obj_id}/", data, format="json")
        force_authenticate(request, user=user)
        return DynamicFormController.as_view()(request, modelName=modelName, id=obj_id)

    def test_customer_cannot_fetch_category_edit_form(self):
        res = self._get("category", self.category.id, self.customer)
        self.assertEqual(res.status_code, 403)

    def test_customer_cannot_edit_category(self):
        res = self._post("category", self.category.id, self.customer,
                          {"name": "Hijacked", "description": "x", "slug": "store-category", "display_order": 0})
        self.assertEqual(res.status_code, 403)
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, "Store Category")

    def test_rider_cannot_fetch_category_edit_form(self):
        res = self._get("category", self.category.id, self.rider)
        self.assertEqual(res.status_code, 403)

    def test_restaurant_cannot_fetch_category_edit_form(self):
        res = self._get("category", self.category.id, self.restaurant)
        self.assertEqual(res.status_code, 403)

    def test_legitimate_domain_root_admin_still_works(self):
        """Must not regress: a real Admin (domain-root, back-office role)
        must keep the widened access this whole mechanism exists for."""
        res = self._get("category", self.category.id, self.owner)
        self.assertEqual(res.status_code, 200)


class DynamicFormCreationAuthorizationTests(TestCase):
    """The create path (id=None) has the same authorization hole as the
    cross-domain edit path above, for every dynamic-form model, not only the
    widened ones: any authenticated Customer/Rider/Restaurant could write a
    new row into catalog.Products, catalog.Categories, inventory.Warehouse or
    accounts.Users under their own domain -- still a real write (it lands in
    admin lists/counts) even though it can't cross tenants. Gated by
    isPlatformStaff on both POST (creation itself) and GET (the blank
    create-form schema) with id=None."""

    def setUp(self):
        self.admin = Users.objects.create_user(
            username="create-gate-admin", email="create-gate-admin@x.com", password="x",
            role="Admin", country="Bangladesh")
        self.customer = Users.objects.create_user(
            username="create-gate-customer", email="create-gate-customer@x.com", password="x",
            role="Customer", country="Bangladesh")

    def _post(self, modelName, user, data):
        request = APIRequestFactory().post(f"/api/getForm/{modelName}/", data, format="json")
        force_authenticate(request, user=user)
        return DynamicFormController.as_view()(request, modelName=modelName)

    def _get(self, modelName, user):
        request = APIRequestFactory().get(f"/api/getForm/{modelName}/")
        force_authenticate(request, user=user)
        return DynamicFormController.as_view()(request, modelName=modelName)

    def test_customer_forbidden_from_creating_category(self):
        res = self._post("category", self.customer,
                          {"name": "Hijack Cat", "description": "d", "display_order": 0, "slug": "hijack-cat"})
        self.assertEqual(res.status_code, 403)
        self.assertFalse(Categories.objects.filter(slug="hijack-cat").exists())

    def test_customer_forbidden_from_creating_product(self):
        cat = Categories.objects.create(
            name="Gate Cat", slug="gate-cat", description="",
            domain_user_id=self.admin, added_by_user_id=self.admin)
        res = self._post("product", self.customer, _product_payload(cat.id))
        self.assertEqual(res.status_code, 403)
        self.assertFalse(Products.objects.filter(slug="df-create-test-product").exists())

    def test_customer_forbidden_from_blank_create_form(self):
        res = self._get("category", self.customer)
        self.assertEqual(res.status_code, 403)

    def test_admin_can_still_create_category(self):
        res = self._post("category", self.admin,
                          {"name": "Real Cat", "description": "d", "display_order": 0, "slug": "real-gate-cat"})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(Categories.objects.filter(slug="real-gate-cat").exists())

    def test_admin_can_still_create_product(self):
        cat = Categories.objects.create(
            name="Gate Cat 2", slug="gate-cat-2", description="",
            domain_user_id=self.admin, added_by_user_id=self.admin)
        res = self._post("product", self.admin, _product_payload(cat.id))
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(Products.objects.filter(slug="df-create-test-product").exists())

    def test_admin_can_still_fetch_blank_create_form(self):
        res = self._get("category", self.admin)
        self.assertEqual(res.status_code, 200)


def _product_payload(category_id):
    return {
        "name": "DF Create Test Product",
        "slug": "df-create-test-product",
        "image": [],
        "description": "d",
        "specifications": {},
        "html_description": "",
        "highlights": [],
        "sku": "DF-CREATE-0001",
        "initial_buying_price": 100,
        "initial_selling_price": 200,
        "dimensions": "0x0x0",
        "uom": "PCS",
        "color": "",
        "tax_percentage": 0,
        "brand": "",
        "brand_model": "",
        "status": "ACTIVE",
        "gender": "UNISEX",
        "available_sizes": [],
        "size_chart": {},
        "material": "",
        "generic_name": "",
        "strength": "",
        "dosage_form": "",
        "manufacturer": "",
        "pack_size": "",
        "requires_prescription": False,
        "seo_title": "",
        "seo_description": "",
        "seo_keywords": [],
        "source_url": "",
        "addition_details": {},
        "category_id": category_id,
    }
