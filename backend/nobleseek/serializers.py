"""Serializers — public ones are deliberately slim for fast mobile loads."""
from rest_framework import serializers

from core.helpers import absolutize_media_url

from .models import (AdConfig, Article, Comment, FlatPage, NewsCategory,
                     Poll, PollOption, PushCampaign, PushDevice, TrendKeyword)


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
        fields = ["id", "headline", "headline_bn", "slug", "excerpt",
                  "hero_image", "hero_image_alt", "category", "category_name",
                  "category_slug", "tags", "is_featured", "is_breaking",
                  "view_count", "read_time_minutes", "published_at", "created_at"]

    def get_hero_image(self, obj):
        return absolute_hero(obj, self.context)


class ArticleDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default="")
    category_slug = serializers.SlugField(source="category.slug", read_only=True, default="")
    json_ld = serializers.SerializerMethodField()
    hero_image = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = ["id", "headline", "headline_bn", "slug", "excerpt", "body_html",
                  "hero_image", "hero_image_alt", "image_credit", "source_name",
                  "source_url", "category", "category_name", "category_slug",
                  "tags", "related_product_ids", "seo_title", "seo_description",
                  "seo_keywords", "is_featured", "is_breaking", "view_count",
                  "read_time_minutes", "published_at", "updated_at", "json_ld"]

    def get_json_ld(self, obj):
        request = self.context.get("request")
        site = "https://fabrything.com"
        if request:
            site = f"{request.scheme}://{request.get_host()}"
        return obj.get_json_ld(site)

    def get_hero_image(self, obj):
        return absolute_hero(obj, self.context)


class ArticleAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ["id", "trend", "category", "headline", "headline_bn", "slug",
                  "excerpt", "body_html", "hero_image", "hero_image_alt",
                  "image_credit", "source_name", "source_url", "tags", "status",
                  "is_featured", "is_breaking", "related_product_ids",
                  "seo_title", "seo_description", "seo_keywords", "fb_post_url",
                  "utm_campaign", "view_count", "read_time_minutes",
                  "published_at", "created_at", "updated_at"]
        read_only_fields = ["id", "view_count", "read_time_minutes",
                            "created_at", "updated_at"]


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
