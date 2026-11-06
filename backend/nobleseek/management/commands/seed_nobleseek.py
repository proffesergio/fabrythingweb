"""Legacy command name retained for callers; category-only reconciliation."""

from django.core.management.base import BaseCommand

from nobleseek.category_catalog import reconcile_categories


class Command(BaseCommand):
    help = "Reconcile NobleSeek categories only (legacy command name)."

    def handle(self, *args, **options):
        changes = reconcile_categories(apply=True)
        self.stdout.write(self.style.SUCCESS(
            f"NobleSeek categories reconciled ({len(changes)} changes); no articles or pages created"))
