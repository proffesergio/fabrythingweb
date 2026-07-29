"""Backfill catalog.Products.size_chart for the 64 already-seeded Fabrilife
fashion products, none of which have one (see
catalog.services_size_chart_backfill for the full explanation of why and how
-- looked up by exact name on fabrilife.com's own public search, since these
products carry no source_url to refetch by URL the way sync_source_prices
does for potakait/canvasit).

Dry run by default, same convention as purge_demo_catalog/
apply_pricing_markup -- makes real network requests (one Algolia search per
candidate product) but never writes to the database without --apply:

    python manage.py backfill_fabrilife_size_chart            # report only
    python manage.py backfill_fabrilife_size_chart --apply     # write

Never deletes or overwrites anything but size_chart, and never touches a
product that already has one.
"""
from django.core.management.base import BaseCommand

from catalog.services_size_chart_backfill import backfill_fabrilife_size_charts

_STATUS_LABEL = {
    "updated": "updated",
    "would_update": "would update",
    "no_match": "no exact-title match on fabrilife.com search",
    "no_chart": "matched, but that product has no size chart either",
    "error": "search request failed",
}


class Command(BaseCommand):
    help = ("Backfill size_chart on seeded Fabrilife products by looking them up "
            "on fabrilife.com's own search. Dry run by default.")

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true",
                             help="Actually write size_chart. Without this it only reports.")

    def handle(self, *args, **options):
        apply_ = options["apply"]
        results = backfill_fabrilife_size_charts(dry_run=not apply_)

        if not results:
            self.stdout.write("No candidate products (every Fabrilife product either "
                               "has no sizes, or already has a size_chart).")
            return

        by_status = {}
        for rec in results:
            by_status.setdefault(rec["status"], []).append(rec)

        for status in ("updated", "would_update", "no_chart", "no_match", "error"):
            recs = by_status.get(status)
            if not recs:
                continue
            self.stdout.write(f"\n{_STATUS_LABEL[status]} ({len(recs)}):")
            for rec in recs:
                extra = f" -- {len(rec['size_chart'])} size(s)" if rec["size_chart"] else ""
                self.stdout.write(f"  #{rec['id']:<5} {rec['slug']:<40} {rec['name']!r}{extra}")

        written = len(by_status.get("updated", []))
        would_write = len(by_status.get("would_update", []))
        if apply_:
            self.stdout.write(self.style.SUCCESS(
                f"\n{written}/{len(results)} product(s) updated with a size_chart."))
        else:
            self.stdout.write(self.style.WARNING(
                f"\nDry run -- {would_write}/{len(results)} product(s) would be updated. "
                f"Re-run with --apply to actually write."))
