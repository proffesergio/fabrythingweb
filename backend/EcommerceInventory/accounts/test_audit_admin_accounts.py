"""audit_admin_accounts: list back-office accounts, delete only the ones
named, and only when they carry no order/content history.

The command exists to clean up the probe account production verification
created via the (now closed) public /api/auth/signup/ hole -- and any other
rogue Admin/Staff/Super Admin accounts a real attacker may have made the same
way.
"""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from accounts.models import Users
from catalog.models import Categories


class AuditAdminAccountsListTests(TestCase):
    def test_lists_back_office_accounts_with_created_at(self):
        Users.objects.create_user(
            username="rogue-admin", email="rogue-admin@x.com", password="x", role="Admin")
        Users.objects.create_user(
            username="a-customer", email="a-customer@x.com", password="x", role="Customer")

        out = StringIO()
        call_command("audit_admin_accounts", stdout=out)
        output = out.getvalue()

        self.assertIn("rogue-admin", output)
        self.assertNotIn("a-customer", output)

    def test_empty_when_no_back_office_accounts(self):
        out = StringIO()
        call_command("audit_admin_accounts", stdout=out)
        self.assertIn("No Admin/Super Admin/Staff accounts", out.getvalue())


class AuditAdminAccountsDeleteTests(TestCase):
    def setUp(self):
        self.probe = Users.objects.create_user(
            username="__probe_no_create", email="__probe@invalid", password="x", role="Admin")

    def test_dry_run_deletes_nothing(self):
        out = StringIO()
        call_command("audit_admin_accounts", "__probe_no_create", stdout=out)
        self.assertTrue(Users.objects.filter(username="__probe_no_create").exists())
        self.assertIn("Dry run", out.getvalue())
        self.assertIn("SAFE to delete", out.getvalue())

    def test_apply_deletes_a_clean_account(self):
        out = StringIO()
        call_command("audit_admin_accounts", "__probe_no_create", "--apply", stdout=out)
        self.assertFalse(Users.objects.filter(username="__probe_no_create").exists())
        self.assertIn("Deleted", out.getvalue())

    def test_lookup_by_email_also_works(self):
        out = StringIO()
        call_command("audit_admin_accounts", "__probe@invalid", "--apply", stdout=out)
        self.assertFalse(Users.objects.filter(username="__probe_no_create").exists())

    def test_refuses_account_with_content_history(self):
        """An admin who owns a category (domain_user_id CASCADE) would take
        that category down with them -- must be refused, not deleted."""
        Categories.objects.create(
            name="Real Category", description="", domain_user_id=self.probe, added_by_user_id=self.probe)

        out = StringIO()
        call_command("audit_admin_accounts", "__probe_no_create", "--apply", stdout=out)

        self.assertTrue(Users.objects.filter(username="__probe_no_create").exists())
        self.assertIn("REFUSED", out.getvalue())

    def test_refuses_account_that_created_other_accounts(self):
        Users.objects.create_user(
            username="child-of-probe", email="child@x.com", password="x", role="Staff",
            added_by_user_id=self.probe)

        out = StringIO()
        call_command("audit_admin_accounts", "__probe_no_create", "--apply", stdout=out)

        self.assertTrue(Users.objects.filter(username="__probe_no_create").exists())
        self.assertIn("REFUSED", out.getvalue())

    def test_non_back_office_role_rejected(self):
        Users.objects.create_user(
            username="a-customer2", email="a-customer2@x.com", password="x", role="Customer")
        out = StringIO()
        call_command("audit_admin_accounts", "a-customer2", "--apply", stdout=out)
        self.assertTrue(Users.objects.filter(username="a-customer2").exists())
        self.assertIn("wrong tool", out.getvalue())

    def test_unknown_identifier_reported_not_crashed(self):
        out = StringIO()
        call_command("audit_admin_accounts", "does-not-exist", stdout=out)
        self.assertIn("no such account", out.getvalue())
