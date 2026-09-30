from django.contrib import admin

from .models import AnalyticsProvider, TrackedEvent


@admin.register(AnalyticsProvider)
class AnalyticsProviderAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "is_enabled", "updated_at")
    list_editable = ("is_enabled",)


@admin.register(TrackedEvent)
class TrackedEventAdmin(admin.ModelAdmin):
    list_display = ("event", "path", "session_id", "user_id", "created_at")
    list_filter = ("event",)
    date_hierarchy = "created_at"
    readonly_fields = ("event", "path", "session_id", "user_id", "params", "created_at")

    def has_add_permission(self, request):
        return False
