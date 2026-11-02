from django.contrib import admin

from .models import Categories, ProductQuestions, ProductReviews, Products, ProductVariant


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ("sku", "size", "color", "price", "discount_price", "stock_quantity", "is_active")


@admin.register(Products)
class ProductsAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "category_id", "initial_selling_price", "discount_price", "status", "total_stock")
    search_fields = ("name", "sku", "brand")
    list_filter = ("status", "gender")
    inlines = [ProductVariantInline]


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("sku", "product", "size", "color", "effective_price", "stock_quantity", "is_active")
    search_fields = ("sku", "product__name")
    list_filter = ("is_active", "size")


@admin.register(Categories)
class CategoriesAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent_id", "display_order")
    search_fields = ("name",)


admin.site.register(ProductReviews)
admin.site.register(ProductQuestions)
