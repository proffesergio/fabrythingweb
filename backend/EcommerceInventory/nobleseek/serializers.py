"""Serializers — public ones are deliberately slim for fast mobile loads."""
from rest_framework import serializers

from .models import AdConfig, Article, NewsCategory, TrendKeyword


class NewsCategorySerializer(serializers.ModelSerializer):
    article_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = NewsCategory
        fields = ["id", "name", "slug", "description", "display_order",
                  "is_active", "article_count"]


class TrendKeywordSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrendKeyword
        fields = ["id", "keyword", "geo", "traffic_score", "traffic_label",
                  "category_hint", "status", "fetched_at", "created_at"]
        read_only_fields = ["id", "fetched_at", "created_at"]


class ArticleListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default="")
    category_slug = serializers.SlugField(source="category.slug", read_only=True, default="")

    class Meta:
        model = Article
        fields = ["id", "headline", "headline_bn", "slug", "excerpt",
                  "hero_image", "hero_image_alt", "category", "category_name",
                  "category_slug", "tags", "is_featured", "is_breaking",
                  "view_count", "read_time_minutes", "published_at", "created_at"]


class ArticleDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default="")
    category_slug = serializers.SlugField(source="category.slug", read_only=True, default="")
    json_ld = serializers.SerializerMethodField()

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
