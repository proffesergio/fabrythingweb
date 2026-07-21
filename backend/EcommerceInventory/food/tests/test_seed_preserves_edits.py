"""Re-running the deploy seeders must never revert an admin's manual edits.

build.sh runs these on EVERY release. When seed_bancharampur used
update_or_create, each deploy silently reset zone names, map centres and active
flags to the hardcoded values — so corrections made in the admin panel lasted
only until the next push.
"""
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from food.models import DeliveryZone, Village


class SeedBancharampurPreservesEditsTests(TestCase):
    def setUp(self):
        call_command("seed_bancharampur", stdout=StringIO())
        self.zone = DeliveryZone.objects.get(name="Purbo Ujanchar")

    def test_seeds_unions_and_villages(self):
        self.assertGreaterEqual(DeliveryZone.objects.count(), 13)
        self.assertGreaterEqual(Village.objects.count(), 100)

    def test_rerun_keeps_manual_bangla_correction(self):
        self.zone.name_bn = "পূর্ব উজানচর ইউনিয়ন"   # admin's corrected spelling
        self.zone.save()

        call_command("seed_bancharampur", stdout=StringIO())

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.name_bn, "পূর্ব উজানচর ইউনিয়ন")

    def test_rerun_keeps_manual_geography_and_active_flag(self):
        self.zone.center_lat = Decimal("23.999999")
        self.zone.radius_km = Decimal("9.50")
        self.zone.is_active = False          # admin deliberately paused this union
        self.zone.save()

        call_command("seed_bancharampur", stdout=StringIO())

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.center_lat, Decimal("23.999999"))
        self.assertEqual(self.zone.radius_km, Decimal("9.50"))
        self.assertFalse(self.zone.is_active, "deploy re-activated a zone the admin paused")

    def test_rerun_keeps_admin_added_villages(self):
        Village.objects.create(zone=self.zone, name="Notun Para", name_bn="নতুন পাড়া")
        call_command("seed_bancharampur", stdout=StringIO())
        self.assertTrue(Village.objects.filter(name="Notun Para").exists())

    def test_rerun_creates_no_duplicates(self):
        before = (DeliveryZone.objects.count(), Village.objects.count())
        call_command("seed_bancharampur", stdout=StringIO())
        self.assertEqual((DeliveryZone.objects.count(), Village.objects.count()), before)

    def test_blank_bangla_name_is_still_backfilled(self):
        self.zone.name_bn = ""
        self.zone.save()
        call_command("seed_bancharampur", stdout=StringIO())
        self.zone.refresh_from_db()
        self.assertEqual(self.zone.name_bn, "পূর্ব উজানচর")

    def test_force_update_restores_canonical_values(self):
        self.zone.name_bn = "ভুল নাম"
        self.zone.is_active = False
        self.zone.save()

        call_command("seed_bancharampur", "--force-update", stdout=StringIO())

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.name_bn, "পূর্ব উজানচর")
        self.assertTrue(self.zone.is_active)
