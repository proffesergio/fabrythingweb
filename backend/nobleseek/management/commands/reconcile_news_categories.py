"""Reconcile the NobleSeek category catalog without changing IDs or slugs."""

from django.core.management.base import BaseCommand

from nobleseek.category_catalog import reconcile_categories


class Command(BaseCommand):
    help = "Preview NobleSeek category changes; --apply creates/updates catalog rows only."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Apply the reported changes")

    def handle(self, *args, **options):
        changes = reconcile_categories(apply=options["apply"])
        mode = "Applied" if options["apply"] else "Dry run"
        self.stdout.write(f"{mode}: {len(changes)} category changes")
        for change in changes:
            self.stdout.write(
                f"{change['action']} id={change.get('id', 'new')} "
                f"slug={change['slug']} name={change['name']} "
                f"display_order={change['display_order']}")
