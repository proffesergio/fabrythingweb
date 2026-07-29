from django.contrib import admin

from .models import StoreConfiguration, WhatsAppAlertLog


@admin.register(StoreConfiguration)
class StoreConfigurationAdmin(admin.ModelAdmin):
    list_display = ("store_name", "fixed_shipping_rate", "free_shipping_threshold", "cod_enabled",
                    "currency", "whatsapp_admin_number")

    def has_add_permission(self, request):
        # Singleton: only allow the one row.
        return not StoreConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(WhatsAppAlertLog)
class WhatsAppAlertLogAdmin(admin.ModelAdmin):
    """Read-only attempt log — see core.whatsapp.send_whatsapp. This is how the
    owner confirms alerts are actually firing once credentials are in, rather
    than discovering a silent no-send weeks later."""
    list_display = ("created_at", "kind", "recipient", "related_order", "success")
    list_filter = ("kind", "success")
    search_fields = ("recipient", "related_order")
    readonly_fields = [f.name for f in WhatsAppAlertLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
