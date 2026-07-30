"""Users.role now defaults to "Customer", not "Admin".

"Admin" as the implicit default was the root hazard behind the
/api/auth/signup/ vulnerability: any code path that created a user without
passing role= explicitly minted a full admin. Every legitimate call site in
this codebase already passes role= explicitly (create_admin, rider/
restaurant/partner onboarding, seeders); this test pins the fallback itself,
and create_admin.py's test pins that Super Admin bootstrap still works.
"""
from django.core.management import call_command
from django.test import TestCase

from accounts.models import Users


class RoleDefaultTests(TestCase):
    def test_create_with_no_role_defaults_to_customer(self):
        user = Users.objects.create_user(
            username="no-role-given", email="no-role-given@x.com", password="x")
        self.assertEqual(user.role, "Customer")

    def test_plain_create_with_no_role_defaults_to_customer(self):
        user = Users.objects.create(
            username="no-role-plain", email="no-role-plain@x.com", password="x")
        self.assertEqual(user.role, "Customer")


class CreateAdminCommandStillCreatesRealAdminTests(TestCase):
    """create_admin passes role="Super Admin" explicitly, so the new
    least-privileged model default must not silently downgrade it."""

    def test_create_admin_yields_a_working_super_admin(self):
        call_command("create_admin", username="bootstrap-admin",
                    email="bootstrap-admin@x.com", password="hunter22")
        user = Users.objects.get(username="bootstrap-admin")
        self.assertEqual(user.role, "Super Admin")
        self.assertEqual(user.domain_user_id_id, user.id)
        self.assertTrue(user.check_password("hunter22"))
