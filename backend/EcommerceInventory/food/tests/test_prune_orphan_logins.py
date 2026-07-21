from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from food.models import Rider, Restaurant

User = get_user_model()


class PruneOrphanLoginsTests(TestCase):
    def setUp(self):
        self.orphan = User.objects.create_user(
            username="orphan_rider", email="orphan@example.com", password="x", role="Rider")
        self.attached = User.objects.create_user(
            username="real_rider", email="real@example.com", password="x", role="Rider")
        Rider.objects.create(user=self.attached, name="Real Rider")

        self.orphan_owner = User.objects.create_user(
            username="orphan_owner", email="oowner@example.com", password="x", role="Restaurant")
        self.attached_owner = User.objects.create_user(
            username="real_owner", email="rowner@example.com", password="x", role="Restaurant")
        Restaurant.objects.create(name="Real Co", slug="real-co", owner=self.attached_owner)

        self.admin = User.objects.create_user(
            username="an_admin", email="an_admin@example.com", password="x", role="Super Admin")

    def test_dry_run_reports_but_deletes_nothing(self):
        out = StringIO()
        call_command("prune_orphan_logins", stdout=out)
        self.assertIn("orphan_rider", out.getvalue())
        self.assertIn("orphan_owner", out.getvalue())
        self.assertTrue(User.objects.filter(username="orphan_rider").exists())

    def test_apply_deletes_only_orphans(self):
        call_command("prune_orphan_logins", "--apply", stdout=StringIO())
        self.assertFalse(User.objects.filter(username="orphan_rider").exists())
        self.assertFalse(User.objects.filter(username="orphan_owner").exists())
        # Attached logins and non-prunable roles must survive.
        self.assertTrue(User.objects.filter(username="real_rider").exists())
        self.assertTrue(User.objects.filter(username="real_owner").exists())
        self.assertTrue(User.objects.filter(username="an_admin").exists())

    def test_role_filter_limits_scope(self):
        call_command("prune_orphan_logins", "--apply", "--role", "Rider", stdout=StringIO())
        self.assertFalse(User.objects.filter(username="orphan_rider").exists())
        self.assertTrue(User.objects.filter(username="orphan_owner").exists())

    def test_reports_nothing_when_clean(self):
        call_command("prune_orphan_logins", "--apply", stdout=StringIO())
        out = StringIO()
        call_command("prune_orphan_logins", stdout=out)
        self.assertIn("No orphan logins found", out.getvalue())
