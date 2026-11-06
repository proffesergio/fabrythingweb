"""Staff publishing controls and measured operational data (no provider quotas)."""
from datetime import timedelta

from django.db import DatabaseError, connection, transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import Trim
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.helpers import renderResponse
from storefront.permissions import IsPlatformStaff
from .models import Article, PublishingSettings
from .serializers import PublishingSettingsSerializer
from .services_publishing import daily_window


def database_size():
    result = {"vendor": connection.vendor, "size_bytes": None, "available": False}
    if connection.vendor != "postgresql":
        return {**result, "reason": "Database size measurement requires PostgreSQL."}
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("SELECT pg_database_size(current_database())")
            size = cursor.fetchone()[0]
        return {**result, "size_bytes": size, "available": True}
    except DatabaseError:
        return {**result, "reason": "Database size measurement unavailable."}


class AdminPublishingSettingsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformStaff]

    def get(self, request):
        return renderResponse(data=PublishingSettingsSerializer(PublishingSettings.current()).data,
                              message="Publishing settings")

    def patch(self, request):
        with transaction.atomic():
            policy = PublishingSettings.locked()
            serializer = PublishingSettingsSerializer(policy, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return renderResponse(data=serializer.data, message="Publishing settings saved")


class AdminOperationsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformStaff]

    def get(self, request):
        now = timezone.now()
        since = now - timedelta(hours=24)
        articles = Article.objects.all()
        counts = articles.aggregate(
            total=Count("pk"),
            news=Count("pk", filter=Q(content_type=Article.ContentType.NEWS)),
            blog=Count("pk", filter=Q(content_type=Article.ContentType.BLOG)),
            drafts=Count("pk", filter=Q(status=Article.Status.DRAFT)),
            review=Count("pk", filter=Q(status=Article.Status.REVIEW)),
            published=Count("pk", filter=Q(status=Article.Status.PUBLISHED, published_at__lte=now)),
            scheduled=Count("pk", filter=Q(status=Article.Status.PUBLISHED, published_at__gt=now)),
            archived=Count("pk", filter=Q(status=Article.Status.ARCHIVED)),
            total_views=Sum("view_count"),
            with_hero_image=Count("pk", filter=~Q(hero_image="")))
        counts["total_views"] = counts["total_views"] or 0
        start, end = daily_window(now)
        counts["created_today"] = articles.filter(created_at__gte=start, created_at__lt=end).count()
        production = articles.aggregate(
            created=Count("pk", filter=Q(created_at__gte=since, created_at__lte=now)),
            news_created=Count("pk", filter=Q(created_at__gte=since, created_at__lte=now,
                                               content_type=Article.ContentType.NEWS)),
            blog_created=Count("pk", filter=Q(created_at__gte=since, created_at__lte=now,
                                               content_type=Article.ContentType.BLOG)),
            published=Count("pk", filter=Q(status=Article.Status.PUBLISHED,
                                             published_at__gte=since, published_at__lte=now)))
        live = articles.filter(status=Article.Status.PUBLISHED, published_at__lte=now).annotate(
            clean_title=Trim("seo_title"), clean_description=Trim("seo_description"),
            clean_image=Trim("hero_image"), clean_alt=Trim("hero_image_alt"))
        missing = {
            "seo_title": Q(clean_title=""), "seo_description": Q(clean_description=""),
            "hero_image": Q(clean_image=""),
            "hero_image_alt": ~Q(clean_image="") & Q(clean_alt=""),
        }
        any_missing = Q()
        for condition in missing.values():
            any_missing |= condition
        seo_counts = live.aggregate(**{key: Count("pk", filter=value) for key, value in missing.items()})
        samples = []
        for article in live.filter(any_missing).order_by("-published_at", "pk")[:10]:
            fields = [field for field in ("seo_title", "seo_description", "hero_image")
                      if not getattr(article, field).strip()]
            if article.hero_image.strip() and not article.hero_image_alt.strip():
                fields.append("hero_image_alt")
            samples.append({"id": article.pk, "slug": article.slug, "headline": article.headline,
                            "content_type": article.content_type, "missing_fields": fields})
        policy = PublishingSettings.current()
        text_bytes = counts["total"] * policy.estimated_text_bytes_per_article
        image_bytes = counts["with_hero_image"] * policy.estimated_image_bytes_per_article
        return renderResponse(data={
            "generated_at": now.isoformat(),
            "counts": counts,
            "production_last_24h": {"since": since.isoformat(), "until": now.isoformat(), **production},
            "seo": {"scope": "live_published_articles", "missing": seo_counts,
                    "articles_with_missing_metadata": live.filter(any_missing).count(),
                    "sample_limit": 10, "samples": samples},
            "database": database_size(),
            "provider_metrics": {"available": False, "reason": "Provider usage, quotas, and billing are not connected.",
                                 "storage_limit_bytes": None, "requests": None, "cost": None},
            "storage_estimate": {
                "is_estimate": True, "text_bytes": text_bytes, "image_bytes": image_bytes,
                "total_bytes": text_bytes + image_bytes,
                "assumptions": {
                    "text_bytes_per_article": policy.estimated_text_bytes_per_article,
                    "image_bytes_per_article": policy.estimated_image_bytes_per_article,
                    "text_article_count": counts["total"], "image_article_count": counts["with_hero_image"],
                    "note": "Text allowance per stored article; one image allowance per nonempty hero URL. "
                            "Excludes indexes, revisions, inline images, replicas, backups, and other application data. "
                            "Image URLs may refer to external storage; this is not measured database usage."}},
        }, message="Publishing operations")
