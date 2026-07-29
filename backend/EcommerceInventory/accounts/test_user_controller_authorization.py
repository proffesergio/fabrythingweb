"""User management (list users, edit a user, grant module permissions) is a
back-office function. Every view in UserController.py was IsAuthenticated
only, with no role check. UpdateUsers is the sharp edge: its serializer
exposes `role`, and a self-signed-up Customer's domain_user_id_id equals
their own id (see core.helpers.isPlatformStaff docstring), so
PATCH /api/auth/updateuser/<own id>/ matched their own row through the
existing domain filter -- letting a plain Customer set their own role to
"Super Admin" via {"role": "Super Admin", ...}. UserPermissionsView.post is
similar: it writes UserPermissions rows for an arbitrary `pk` with no role
check at all.

Fixed by gating on the role axis (core.helpers.PLATFORM_STAFF_ROLES), not the
full isPlatformStaff predicate -- these views already scope by the caller's
own domain_user_id_id, so a legitimate non-root Staff/Admin sub-account must
keep managing its own tenant's users.
"""
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.controllers.UserController import (
    UpdateUsers,
    UserListView,
    UserPermissionsView,
    UserWithFilterListView,
)
from accounts.models import Modules, UserPermissions, Users


class UserControllerAuthorizationTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.admin = Users.objects.create_user(
            username="uc-admin", email="uc-admin@x.com", password="x",
            role="Admin", country="Bangladesh")
        self.customer = Users.objects.create_user(
            username="uc-customer", email="uc-customer@x.com", password="x",
            role="Customer", country="Bangladesh")
        self.module = Modules.objects.create(module_name="UC Test Module")

    def test_customer_forbidden_from_user_list(self):
        request = self.factory.get("/api/auth/users/")
        force_authenticate(request, user=self.customer)
        res = UserListView.as_view()(request)
        self.assertEqual(res.status_code, 403)

    def test_customer_forbidden_from_filtered_user_list(self):
        request = self.factory.get("/api/auth/userlist/")
        force_authenticate(request, user=self.customer)
        res = UserWithFilterListView.as_view()(request)
        self.assertEqual(res.status_code, 403)

    def test_customer_cannot_escalate_own_role_via_update_users(self):
        """CRITICAL regression: a self-signed-up Customer is its own domain
        root, so PATCH /api/auth/updateuser/<own id>/ matched their own row
        under the pre-fix domain filter -- and the serializer exposes `role`."""
        request = self.factory.patch(
            f"/api/auth/updateuser/{self.customer.id}/",
            {"role": "Super Admin"}, format="json")
        force_authenticate(request, user=self.customer)
        res = UpdateUsers.as_view()(request, pk=self.customer.id)
        self.assertEqual(res.status_code, 403)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.role, "Customer")

    def test_customer_forbidden_from_granting_permissions(self):
        request = self.factory.post(
            f"/api/auth/userpermission/{self.customer.id}/",
            [{"module_id": self.module.id, "is_permission": True}], format="json")
        force_authenticate(request, user=self.customer)
        res = UserPermissionsView.as_view()(request, pk=self.customer.id)
        self.assertEqual(res.status_code, 403)
        self.assertFalse(UserPermissions.objects.filter(user=self.customer.id).exists())

    def test_customer_forbidden_from_reading_permissions(self):
        request = self.factory.get(f"/api/auth/userpermission/{self.customer.id}/")
        force_authenticate(request, user=self.customer)
        res = UserPermissionsView.as_view()(request, pk=self.customer.id)
        self.assertEqual(res.status_code, 403)

    def test_admin_can_still_list_users(self):
        request = self.factory.get("/api/auth/users/")
        force_authenticate(request, user=self.admin)
        res = UserListView.as_view()(request)
        self.assertEqual(res.status_code, 200)

    def test_admin_can_still_update_own_user(self):
        request = self.factory.patch(
            f"/api/auth/updateuser/{self.admin.id}/",
            {"first_name": "Updated"}, format="json")
        force_authenticate(request, user=self.admin)
        res = UpdateUsers.as_view()(request, pk=self.admin.id)
        self.assertEqual(res.status_code, 200, res.data)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.first_name, "Updated")

    def test_admin_can_still_grant_permissions(self):
        request = self.factory.post(
            f"/api/auth/userpermission/{self.admin.id}/",
            [{"module_id": self.module.id, "is_permission": True}], format="json")
        force_authenticate(request, user=self.admin)
        res = UserPermissionsView.as_view()(request, pk=self.admin.id)
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(UserPermissions.objects.filter(user=self.admin.id, module=self.module).exists())
