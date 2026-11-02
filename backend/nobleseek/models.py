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
    # Optional parent for sub-sections (e.g. খেলা > ক্রিকেট). Null = top level.
    parent = models.ForeignKey("self", null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="children")
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
            "author": {"@type": "Organization", "name": "NobleSeek",
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


class FlatPage(models.Model):
    """Editable trust/info pages (about, contact, privacy…). The portal
    renders these when the API answers and falls back to built-in copy
    otherwise — editing copy never needs a redeploy."""

    slug = models.SlugField(max_length=80, unique=True,
                            help_text="about | contact | privacy | disclaimer | ethics…")
    title = models.CharField(max_length=200)
    intro = models.CharField(max_length=300, blank=True, default="")
    body_html = models.TextField()
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["slug"]

    def __str__(self):
        return f"{self.title} (/{self.slug})"


class Comment(models.Model):
    """On-site reader comments (Facebook embed stays as-is). New comments
    land PENDING — nothing public until the desk approves it."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    article = models.ForeignKey(Article, on_delete=models.CASCADE,
                                related_name="comments")
    name = models.CharField(max_length=80)
    text = models.CharField(max_length=500)
    status = models.CharField(max_length=10, choices=Status.choices,
                              default=Status.PENDING, db_index=True)
    flags = models.PositiveIntegerField(default=0,
                                        help_text="Reader reports; moderation queue sorts by this")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["article", "status"])]

    def __str__(self):
        return f"{self.name} on {self.article_id} [{self.status}]"


class PushDevice(models.Model):
    """Push subscriber token (app or, later, web). Tokens are opaque strings;
    sending happens through FCM and degrades to logged-skip without a key."""

    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=16, default="android",
                                help_text="android | ios | web")
    topics = models.JSONField(default=list, blank=True,
                              help_text='e.g. ["breaking","sports"]')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.platform}:{self.token[:12]}…"


class PushCampaign(models.Model):
    """One manual send from the desk: what went out, to how many, result."""

    title = models.CharField(max_length=120)
    body = models.CharField(max_length=300)
    url = models.URLField(max_length=500, blank=True, default="")
    audience = models.PositiveIntegerField(default=0)
    sent = models.PositiveIntegerField(default=0)
    failed = models.PositiveIntegerField(default=0)
    skipped = models.PositiveIntegerField(default=0)
    note = models.CharField(max_length=300, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.sent}/{self.audience})"


class Poll(models.Model):
    """Reader poll with one-vote-per-browser enforcement (session key)."""

    question = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.question[:60]

    def results(self):
        from django.db.models import Count
        total = self.votes.count()
        opts = list(self.options.annotate(n=Count("votes")).order_by("display_order"))
        return {
            "id": self.id, "question": self.question, "total": total,
            "options": [{"id": o.id, "text": o.text, "votes": o.n,
                         "pct": round(o.n / total * 100, 1) if total else 0.0}
                        for o in opts],
        }


class PollOption(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=200)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order"]

    def __str__(self):
        return f"{self.poll_id}: {self.text[:40]}"


class PollVote(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="votes")
    option = models.ForeignKey(PollOption, on_delete=models.CASCADE, related_name="votes")
    session_key = models.CharField(max_length=64, db_index=True,
                                   help_text="Client UUID in localStorage — one vote per browser")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["poll", "session_key"], name="uq_vote_poll_session")]
