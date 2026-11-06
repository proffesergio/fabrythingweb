"""Explicit, idempotent domain activation after migration and DNS verification."""
import json

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, transaction

from nobleseek.models import PublishingSettings


class Command(BaseCommand):
    help = "Activate the verified NobleSeek origin without changing ingestion policy."

    def add_arguments(self, parser):
        parser.add_argument("--origin", required=True)
        parser.add_argument("--if-default", action="store_true",
                            help="Change only the legacy www origin; preserve saved custom origins.")

    def handle(self, *args, **options):
        origin = options["origin"]
        if origin != "https://nobleseek.fabrything.com":
            raise CommandError("Origin must be exactly https://nobleseek.fabrything.com")
        try:
            with transaction.atomic():
                policy = PublishingSettings.locked()
                eligible = (not options["if_default"]
                            or policy.news_site_url.rstrip("/") == "https://www.fabrything.com")
                changed = eligible and policy.news_site_url != origin
                if changed:
                    policy.news_site_url = origin
                    policy.save(update_fields=["news_site_url", "updated_at"])
        except DatabaseError:
            raise CommandError("News origin activation failed; verify database access and applied migrations.") from None
        self.stdout.write(json.dumps({"news_site_url": policy.news_site_url, "changed": changed}))
