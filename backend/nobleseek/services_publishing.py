"""Shared gate for API and trend article creation, serialized on the policy row."""
from datetime import datetime, time, timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Article, PublishingSettings
from .sanitization import sanitize_article_html


def daily_window(now=None):
    today = timezone.localdate(now)
    tz = timezone.get_current_timezone()
    return (timezone.make_aware(datetime.combine(today, time.min), tz),
            timezone.make_aware(datetime.combine(today + timedelta(days=1), time.min), tz))


@transaction.atomic
def create_article(data, *, automation=False):
    policy = PublishingSettings.locked()
    if policy.ingestion_paused:
        raise ValidationError({"ingestion_paused": "Article ingestion is paused."})
    start, end = daily_window()
    if policy.daily_article_limit and Article.objects.filter(
            created_at__gte=start, created_at__lt=end).count() >= policy.daily_article_limit:
        raise ValidationError({"daily_article_limit": "Daily article creation limit reached."})
    data = dict(data)
    if automation and policy.require_review_for_automation and data.get("status") == Article.Status.PUBLISHED:
        data["status"] = Article.Status.REVIEW
    if "body_html" in data:
        data["body_html"] = sanitize_article_html(data["body_html"])
    return Article.objects.create(**data)
