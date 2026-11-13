from typing import ClassVar

from django.contrib import admin

from .models import (
    CapacitySnapshot,
    ImageCleanupJob,
    OperationsPolicy,
    OrderAlert,
    WorkerHeartbeat,
)


@admin.register(OperationsPolicy)
class PolicyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not OperationsPolicy.objects.exists()


@admin.register(OrderAlert, CapacitySnapshot, WorkerHeartbeat)
class OperationsHistoryAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False


@admin.register(ImageCleanupJob)
class ImageCleanupAdmin(OperationsHistoryAdmin):
    list_display: ClassVar[list] = [
        "product",
        "slot",
        "status",
        "attempts",
        "updated_at",
    ]
    list_filter: ClassVar[list] = ["status"]
    search_fields: ClassVar[list] = ["product__name", "product__sku"]
    actions: ClassVar[list] = ["retry_failed", "restore_originals"]

    @admin.action(description="Retry failed/review photos")
    def retry_failed(self, request, queryset):
        from django.utils import timezone

        count = queryset.filter(status__in=["failed", "review"]).update(
            status="queued", attempts=0, error="", updated_at=timezone.now()
        )
        self.message_user(request, f"{count} photos queued for retry.")

    @admin.action(description="Restore completed photos to retained originals")
    def restore_originals(self, request, queryset):
        from .images import restore_job

        count = 0
        for job in queryset.filter(status="completed")[:100]:
            try:
                restore_job(job.pk)
                count += 1
            except ValueError:
                pass
        self.message_user(
            request, f"{count} originals restored. Changed photos were skipped."
        )
