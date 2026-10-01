"""NobleSeek news models — Google-Trends-driven editorial layer.

Design notes:
- TrendKeyword is append-only inbox (cron writes, admin consumes). Never
  edited into articles directly; Article optionally FKs it for attribution.
- Article.body_html stores sanitized HTML from admin rich-text. Frontend
  renders it and injects in-article AdSense slots every ~300 words.
- view_count is denormalized counter incremented on detail GET (throttled
  by IP in view layer, not here).
"""
import math
import re

from django.db import models
from django.utils import timezone
from django.utils.text import slugify


def estimate_read_time_minutes(html: str) -> int:
    text = re.sub(r"<[^>]+>", " ", html or "")
    words = len([w for w in text.split() if w.strip()])
    # Bangla + English mixed avg ~200 wpm, min 1, round up.
    return max(1, math.ceil(words / 200))


def unique_slug(base: str, model_cls, instance_id=None) -> str:
    slug = slugify(base, allow_unicode=True)[:180] or "news"
    # allow_unicode keeps Bangla slugs readable; fallback ascii.
    if not slug.strip("-"):
        slug = slugify(base)[:180] or "news"
    candidate, i = slug, 2
    qs = model_cls.objects.all()
    if instance_id:
        qs = qs.exclude(pk=instance_id)
    while qs.filter(slug=candidate).exists():
        suffix = f"-{i}"
        candidate = f"{slug[:180 - len(suffix)]}{suffix}"
        i += 1
    return candidate


class NewsCategory(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.CharField(max_length=300, blank=True, default="")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name = "News category"
        verbose_name_plural = "News categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self.name, NewsCategory, self.pk)
        super().save(*args, **kwargs)


class TrendKeyword(models.Model):
    class Status(models.TextChoices):
        NEW = "NEW", "New"
        USED = "USED", "Used (draft created)"
        IGNORED = "IGNORED", "Ignored"

    keyword = models.CharField(max_length=255, db_index=True)
    geo = models.CharField(max_length=8, default="BD", help_text="BD or US (trends region)")
    traffic_score = models.IntegerField(default=0, help_text="Relative interest 0-100 or search volume")
    traffic_label = models.CharField(max_length=60, blank=True, default="", help_text="e.g. 200K+ searches")
    category_hint = models.CharField(max_length=120, blank=True, default="")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.NEW)
    fetched_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-traffic_score", "-fetched_at"]
        indexes = [models.Index(fields=["status", "-fetched_at"])]
        verbose_name = "Trend keyword"
        verbose_name_plural = "Trend keywords"

    def __str__(self):
        return f"[{self.geo}] {self.keyword} ({self.traffic_score})"


class Article(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        REVIEW = "REVIEW", "In review"
        PUBLISHED = "PUBLISHED", "Published"
        ARCHIVED = "ARCHIVED", "Archived"

    trend = models.ForeignKey(TrendKeyword, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="articles")
    category = models.ForeignKey(NewsCategory, null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name="articles")
    headline = models.CharField(max_length=255, help_text="Engaging headline (Bangla viral + EN keyword)")
    headline_bn = models.CharField(max_length=255, blank=True, default="",
                                   help_text="Optional pure-Bangla display headline")
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    excerpt = models.CharField(max_length=300, blank=True, default="",
                               help_text="1-2 lines shown on cards + meta description fallback")
    body_html = models.TextField(help_text="Full 600-1000 word article HTML from admin editor")
    hero_image = models.CharField(max_length=500, blank=True, default="",
                                  help_text="Upload via POST /api/uploads/ then paste URL here")
    hero_image_alt = models.CharField(max_length=255, blank=True, default="")
    image_credit = models.CharField(max_length=255, blank=True, default="")
    source_name = models.CharField(max_length=255, blank=True, default="")
    source_url = models.URLField(max_length=500, blank=True, default="")
    tags = models.JSONField(default=list, blank=True, help_text='e.g. ["cricket","bangladesh"]')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True)
    is_featured = models.BooleanField(default=False)
    is_breaking = models.BooleanField(default=False)
    # Shop funnel: optional related product ids (catalog.Products PKs).
    related_product_ids = models.JSONField(default=list, blank=True)
    seo_title = models.CharField(max_length=255, blank=True, default="")
    seo_description = models.CharField(max_length=300, blank=True, default="")
    seo_keywords = models.JSONField(default=list, blank=True)
    fb_post_url = models.URLField(max_length=500, blank=True, default="",
                                  help_text="Link back to NobleSeek FB post for traffic proof")
    utm_campaign = models.CharField(max_length=120, blank=True, default="nobleseek-fb")
    view_count = models.PositiveIntegerField(default=0)
    read_time_minutes = models.PositiveSmallIntegerField(default=3)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "-published_at"]),
            models.Index(fields=["category", "status"]),
        ]

    def __str__(self):
        return f"{self.headline[:60]} [{self.status}]"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self.headline, Article, self.pk if self.pk else None)
        if self.body_html:
            self.read_time_minutes = estimate_read_time_minutes(self.body_html)
        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        if self.status != self.Status.PUBLISHED and not self.published_at:
            pass  # drafts keep null; ordering falls back to created_at
        super().save(*args, **kwargs)

    @property
    def effective_headline(self) -> str:
        return self.headline_bn or self.headline

    def get_json_ld(self, site_url: str) -> dict:
        return {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": self.headline,
            "description": self.seo_description or self.excerpt,
            "image": [self.hero_image] if self.hero_image else [],
            "datePublished": self.published_at.isoformat() if self.published_at else None,
            "dateModified": self.updated_at.isoformat() if self.updated_at else None,
            "author": {"@type": "Organization", "name": "NobleSeek by Fabrything",
                       "url": site_url},
            "publisher": {"@type": "Organization", "name": "NobleSeek",
                          "logo": {"@type": "ImageObject",
                                   "url": f"{site_url.rstrip('/')}/logo192.png"}},
            "mainEntityOfPage": {"@type": "WebPage",
                                 "@id": f"{site_url.rstrip('/')}/nobleseek/{self.slug}"},
        }


class AdConfig(models.Model):
    """Singleton (pk=1) controlling AdSense density. Frontend reads it via
    public /api/store/nobleseek/ad-config/ and <AdSlot/> hides itself when
    disabled — so you can kill shop ads without redeploying."""

    adsense_client = models.CharField(max_length=64, blank=True, default="",
                                      help_text="ca-pub-XXXXXXXXXXXXXXXX")
    # Manual slot ids created in AdSense > Ads > By site > New ad unit.
    slot_top = models.CharField(max_length=32, blank=True, default="")
    slot_inarticle_1 = models.CharField(max_length=32, blank=True, default="")
    slot_inarticle_2 = models.CharField(max_length=32, blank=True, default="")
    slot_sidebar = models.CharField(max_length=32, blank=True, default="")
    slot_multiplex = models.CharField(max_length=32, blank=True, default="")
    slot_shop_subtle = models.CharField(max_length=32, blank=True, default="")
    # Density switches
    auto_ads_low_sitewide = models.BooleanField(default=True)
    news_detail_max_ads = models.BooleanField(default=True)
    shop_ads_enabled = models.BooleanField(default=False,
                                           help_text="Keep OFF to minimize shop ads")
    anchor_on_news_only = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ad config"
        verbose_name_plural = "Ad config"

    def __str__(self):
        return f"AdConfig client={self.adsense_client or '-'}"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
