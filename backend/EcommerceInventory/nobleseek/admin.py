from django.contrib import admin

from .models import AdConfig, Article, NewsCategory, TrendKeyword


@admin.register(NewsCategory)
class NewsCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "display_order", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("display_order", "is_active")


@admin.register(TrendKeyword)
class TrendKeywordAdmin(admin.ModelAdmin):
    list_display = ("keyword", "geo", "traffic_score", "status", "fetched_at")
    list_filter = ("geo", "status")
    search_fields = ("keyword",)
    actions = ["mark_ignored"]

    @admin.action(description="Mark selected as ignored")
    def mark_ignored(self, request, queryset):
        queryset.update(status=TrendKeyword.Status.IGNORED)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("headline", "category", "status", "is_featured",
                    "is_breaking", "view_count", "published_at")
    list_filter = ("status", "category", "is_featured", "is_breaking")
    search_fields = ("headline", "headline_bn", "slug", "tags")
    prepopulated_fields = {"slug": ("headline",)}
    actions = ["publish_now", "unpublish"]

    @admin.action(description="Publish now")
    def publish_now(self, request, queryset):
        from django.utils import timezone
        queryset.update(status=Article.Status.PUBLISHED, published_at=timezone.now())

    @admin.action(description="Move back to draft")
    def unpublish(self, request, queryset):
        queryset.update(status=Article.Status.DRAFT)


@admin.register(AdConfig)
class AdConfigAdmin(admin.ModelAdmin):
    list_display = ("adsense_client", "shop_ads_enabled",
                    "news_detail_max_ads", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
