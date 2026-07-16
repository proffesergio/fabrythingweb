from django.contrib import admin

from .models import StoreConfiguration


@admin.register(StoreConfiguration)
class StoreConfigurationAdmin(admin.ModelAdmin):
    list_display = ("store_name", "fixed_shipping_rate", "free_shipping_threshold", "cod_enabled", "currency")

    def has_add_permission(self, request):
        # Singleton: only allow the one row.
        return not StoreConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
