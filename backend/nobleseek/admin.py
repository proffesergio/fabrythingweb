from django.contrib import admin

from .models import (AdConfig, Article, Comment, FlatPage, NewsCategory,
                     Poll, PollOption, PollVote, PushCampaign, PushDevice,
                     TrendKeyword)


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


@admin.register(FlatPage)
class FlatPageAdmin(admin.ModelAdmin):
    list_display = ("slug", "title", "is_active", "updated_at")
    list_editable = ("is_active",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("article", "name", "status", "flags", "created_at")
    list_filter = ("status",)
    actions = ["approve", "reject"]

    @admin.action(description="Approve")
    def approve(self, request, queryset):
        queryset.update(status=Comment.Status.APPROVED)

    @admin.action(description="Reject")
    def reject(self, request, queryset):
        queryset.update(status=Comment.Status.REJECTED)


@admin.register(PushDevice)
class PushDeviceAdmin(admin.ModelAdmin):
    list_display = ("token", "platform", "is_active", "created_at")
    list_filter = ("platform", "is_active")


@admin.register(PushCampaign)
class PushCampaignAdmin(admin.ModelAdmin):
    list_display = ("title", "audience", "sent", "failed", "skipped", "created_at")


class PollOptionInline(admin.TabularInline):
    model = PollOption
    extra = 2


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = ("question", "is_active", "created_at")
    list_editable = ("is_active",)
    inlines = [PollOptionInline]
