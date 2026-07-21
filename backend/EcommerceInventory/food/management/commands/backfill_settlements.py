"""Create settlement rows for orders delivered before the settlement ledger existed.

Idempotent — settle_order() no-ops on an order that already has one, so this is
safe to run on every deploy (build.sh does exactly that).
"""
from django.core.management.base import BaseCommand

from food.services_settlement import backfill_settlements


class Command(BaseCommand):
    help = "Backfill OrderSettlement rows for already-delivered food orders."

    def handle(self, *args, **options):
        created = backfill_settlements()
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created {created} settlement(s)."))
        else:
            self.stdout.write("All delivered orders already have settlements.")
