from django.contrib import admin

from .models import Order, OrderItem, OrderStatusLog


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "sku", "size", "color", "unit_price", "quantity", "line_total")
    can_delete = False


class OrderStatusLogInline(admin.TabularInline):
    model = OrderStatusLog
    extra = 0
    readonly_fields = ("from_status", "to_status", "changed_by", "reason", "created_at")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "customer", "status", "total_amount", "contact_phone", "created_at")
    list_filter = ("status", "payment_method", "created_at")
    search_fields = ("order_number", "contact_phone", "contact_name", "customer__username")
    readonly_fields = ("order_number", "subtotal", "shipping_amount", "total_amount", "stock_restored", "created_at", "updated_at")
    inlines = [OrderItemInline, OrderStatusLogInline]
