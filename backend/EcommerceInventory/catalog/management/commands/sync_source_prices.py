from django.core.management.base import BaseCommand

from catalog.services_price_sync import sync_source_prices


class Command(BaseCommand):
    help = "Re-fetch partner-store prices for products with a source_url."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        changes = sync_source_prices(dry_run=options["dry_run"])
        for c in changes:
            mark = "~" if c["updated"] else "!"
            self.stdout.write(f" {mark} {c['slug']}: {c['old_price']} -> {c['new_price']}")
        n = sum(1 for c in changes if c["updated"])
        self.stdout.write(self.style.SUCCESS(
            f"{'DRY RUN: ' if options['dry_run'] else ''}{n}/{len(changes)} updated."))
