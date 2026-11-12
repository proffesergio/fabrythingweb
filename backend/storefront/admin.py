from django.contrib import admin

from .models import Cart, CartItem
from .journal_models import TopicCluster, JournalArticle


@admin.register(TopicCluster)
class TopicClusterAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'parent', 'active')
    list_filter = ('level', 'active')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(JournalArticle)
class JournalArticleAdmin(admin.ModelAdmin):
    list_display = ('article', 'cluster', 'intent', 'created_at')
    readonly_fields = ('source_key', 'payload_hash', 'created_at', 'blocks', 'products', 'sources', 'editorial')


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "updated_at")
    inlines = [CartItemInline]
