"""Serializers — public ones are deliberately slim for fast mobile loads."""
from rest_framework import serializers
from urllib.parse import urlsplit

from core.helpers import absolutize_media_url

from .models import (AdConfig, Article, Comment, FlatPage, NewsCategory,
                     Poll, PollOption, PublishingSettings, PushCampaign, PushDevice, TrendKeyword)
from .sanitization import sanitize_article_html


def absolute_hero(obj, context):
    """hero_image may be a relative DB-blob path (/api/media/<sha>/) which is
    meaningless on the storefront origin — absolutize at serialization time
    (same contract as catalog images; see core.helpers)."""
    request = (context or {}).get("request")
    return absolutize_media_url(obj.hero_image, request)


class NewsCategorySerializer(serializers.ModelSerializer):
    article_count = serializers.IntegerField(read_only=True, default=0)
    parent_name = serializers.CharField(source="parent.name", read_only=True, default="")

    class Meta:
        model = NewsCategory
        fields = ["id", "name", "slug", "description", "display_order",
                  "is_active", "parent", "parent_name", "article_count"]


class TrendKeywordSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrendKeyword
        fields = ["id", "keyword", "geo", "traffic_score", "traffic_label",
                  "category_hint", "status", "fetched_at", "created_at"]
        read_only_fields = ["id", "fetched_at", "created_at"]


class ArticleListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default="")
    category_slug = serializers.SlugField(source="category.slug", read_only=True, default="")
    hero_image = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = ["id", "content_type", "headline", "headline_bn", "slug", "excerpt",
                  "hero_image", "hero_image_alt", "category", "category_name",
                  "category_slug", "tags", "is_featured", "is_breaking",
                  "view_count", "read_time_minutes", "published_at", "created_at"]

    def get_hero_image(self, obj):
        return absolute_hero(obj, self.context)


class ArticleDetailSerializer(serializers.ModelSerializer):
    journal = serializers.SerializerMethodField()
    category_name = serializers.CharField(source="category.name", read_only=True, default="")
    category_slug = serializers.SlugField(source="category.slug", read_only=True, default="")
    json_ld = serializers.SerializerMethodField()
    hero_image = serializers.SerializerMethodField()
    canonical_url = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = ["id", "content_type", "headline", "headline_bn", "slug", "excerpt", "body_html",
                  "hero_image", "hero_image_alt", "image_credit", "source_name",
                  "source_url", "category", "category_name", "category_slug",
                  "tags", "related_product_ids", "seo_title", "seo_description",
                  "seo_keywords", "is_featured", "is_breaking", "view_count",
                  "read_time_minutes", "published_at", "updated_at", "json_ld", "canonical_url", "journal"]

    def get_journal(self, obj):
        if obj.content_type != Article.ContentType.BLOG:
            return None
        from storefront.journal import journal_data
        return journal_data(obj)

    def get_canonical_url(self, obj):
        return obj.get_canonical_url()

    def get_json_ld(self, obj):
        if obj.content_type == Article.ContentType.BLOG:
            from storefront.journal import journal_json_ld, journal_data
            if journal_data(obj):
                return journal_json_ld(obj)
        data = obj.get_json_ld()
        data["image"] = [absolute_hero(obj, self.context)] if obj.hero_image else []
        return data

    def get_hero_image(self, obj):
        return absolute_hero(obj, self.context)


class ArticleAdminSerializer(serializers.ModelSerializer):
    automation = serializers.BooleanField(write_only=True, required=False, default=False)

    def validate_body_html(self, value):
        return sanitize_article_html(value)

    def create(self, validated_data):
        from .services_publishing import create_article
        automation = validated_data.pop("automation", False)
        return create_article(validated_data, automation=automation)

    def update(self, instance, validated_data):
        validated_data.pop("automation", None)
        return super().update(instance, validated_data)

    class Meta:
        model = Article
        fields = ["id", "content_type", "automation", "trend", "category", "headline", "headline_bn", "slug",
                  "excerpt", "body_html", "hero_image", "hero_image_alt",
                  "image_credit", "source_name", "source_url", "tags", "status",
                  "is_featured", "is_breaking", "related_product_ids",
                  "seo_title", "seo_description", "seo_keywords", "fb_post_url",
                  "utm_campaign", "view_count", "read_time_minutes",
                  "published_at", "created_at", "updated_at"]
        read_only_fields = ["id", "view_count", "read_time_minutes",
                            "created_at", "updated_at"]


class PublishingSettingsSerializer(serializers.ModelSerializer):
    def validate_news_site_url(self, value):
        parsed = urlsplit(value)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in {"", "/"}):
            raise serializers.ValidationError("Use an HTTP(S) origin without a path, credentials, query, or fragment.")
        return value.rstrip("/")

    class Meta:
        model = PublishingSettings
        fields = ["news_site_url", "ingestion_paused", "daily_article_limit",
                  "require_review_for_automation", "estimated_text_bytes_per_article",
                  "estimated_image_bytes_per_article", "updated_at"]
        read_only_fields = ["updated_at"]


class AdConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdConfig
        fields = ["adsense_client", "slot_top", "slot_inarticle_1",
                  "slot_inarticle_2", "slot_sidebar", "slot_multiplex",
                  "slot_shop_subtle", "auto_ads_low_sitewide",
                  "news_detail_max_ads", "shop_ads_enabled",
                  "anchor_on_news_only"]


class FlatPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlatPage
        fields = ["slug", "title", "intro", "body_html", "updated_at"]


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ["id", "article", "name", "text", "status", "flags",
                  "created_at"]
        read_only_fields = ["id", "status", "flags", "created_at"]


class PushDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushDevice
        fields = ["token", "platform", "topics"]


class PollResultsSerializer(serializers.Serializer):
    """Read-only aggregate shape from Poll.results()."""
    id = serializers.IntegerField()
    question = serializers.CharField()
    total = serializers.IntegerField()
    options = serializers.ListField(child=serializers.DictField())


class PushCampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushCampaign
        fields = ["id", "title", "body", "url", "audience", "sent",
                  "failed", "skipped", "note", "created_at"]
        read_only_fields = ["id", "audience", "sent", "failed", "skipped",
                            "note", "created_at"]
