"""Aggregate capacity evidence with no credentials, article content, or URLs."""
import json
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connection, transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from core.models import ImageBlob
from catalog.models import Products
from nobleseek.models import Article, PublishingSettings
from nobleseek.views_operations import database_size


class Command(BaseCommand):
    help = "Print read-only publishing counts, database size, and storage configuration flags."

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                if connection.vendor == "postgresql":
                    with connection.cursor() as cursor:
                        cursor.execute("SET TRANSACTION READ ONLY")
                now = timezone.now()
                counts = Article.objects.aggregate(
                    total=Count("pk"), news=Count("pk", filter=Q(content_type="NEWS")),
                    blog=Count("pk", filter=Q(content_type="BLOG")),
                    live_published=Count("pk", filter=Q(status="PUBLISHED", published_at__lte=now)),
                    created_last_24h=Count("pk", filter=Q(created_at__gte=now - timedelta(hours=24), created_at__lte=now)),
                    with_recorded_facebook_link=Count("pk", filter=~Q(fb_post_url="")))
                images = ImageBlob.objects.aggregate(count=Count("pk"), payload_bytes=Sum("byte_size"))
                images["payload_bytes"] = images["payload_bytes"] or 0
                catalog = Products.objects.aggregate(
                    total=Count("pk"), active=Count("pk", filter=Q(status="ACTIVE")))
                policy = PublishingSettings.current()
                result = {
                    "counts": counts, "catalog": catalog,
                    "database": database_size(), "database_images": images,
                    "storage_configuration": {
                        "bucket_configured": bool(getattr(settings, "AWS_STORAGE_BUCKET_NAME", "")),
                        "endpoint_configured": bool(getattr(settings, "AWS_S3_ENDPOINT_URL", "")),
                        "public_base_url_configured": bool(getattr(settings, "AWS_S3_PUBLIC_BASE_URL", "")),
                        "access_key_configured": bool(getattr(settings, "AWS_ACCESS_KEY_ID", "")),
                        "secret_key_configured": bool(getattr(settings, "AWS_ACESS_KEY_SECRET", ""))},
                    "storage_assumptions": {
                        "text_bytes_per_article": policy.estimated_text_bytes_per_article,
                        "image_bytes_per_article": policy.estimated_image_bytes_per_article},
                    "provider_metrics_available": False}
        except DatabaseError:
            raise CommandError("Capacity measurement failed; verify database access and applied migrations.") from None
        self.stdout.write(json.dumps(result))
