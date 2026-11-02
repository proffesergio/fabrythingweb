from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Fetch Google Trends (BD + US) into TrendKeyword inbox. Run 2x daily via cron."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20)

    def handle(self, *args, **opts):
        from nobleseek.services_trends import fetch_and_store
        n = fetch_and_store(limit_per_geo=opts["limit"])
        self.stdout.write(self.style.SUCCESS(f"Imported {n} new trend keywords"))
