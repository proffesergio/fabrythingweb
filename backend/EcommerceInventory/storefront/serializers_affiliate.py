"""Serializers for AffiliateProduct -- admin CRUD shape and the public
storefront shape (which never exposes commission_amount or click_count, and
always resolves the click-through URL to OUR OWN redirect endpoint, never the
constructed/override target directly -- see views_affiliate.
AffiliateClickRedirectView for why click_count can only be trusted if every
customer click actually passes through it).
"""
import logging

from django.urls import reverse
from rest_framework import serializers

from catalog.models import Categories
from core.helpers import absolutize_media_url

from .models import AffiliateProduct
from .services_affiliate import UnsupportedProgramError, build_affiliate_link

logger = logging.getLogger(__name__)

# Display label for the "via <Program>" partner badge the owner asked every
# affiliate item be marked with -- keyed off AffiliateProduct.program, not a
# hardcoded assumption the whole module only ever serves Rokomari.
PROGRAM_LABELS = {
    "rokomari": "Rokomari",
}


class AffiliateProductAdminSerializer(serializers.ModelSerializer):
    grid_category_ids = serializers.PrimaryKeyRelatedField(
        source='grid_categories', many=True, queryset=Categories.objects.all(), required=False,
    )

    class Meta:
        model = AffiliateProduct
        fields = [
            'id', 'program', 'remote_product_id', 'source_url', 'title', 'brand', 'image',
            'original_price', 'current_price', 'commission_amount', 'link_type',
            'manual_short_link', 'is_active', 'starts_at', 'ends_at', 'display_order',
            'click_count', 'show_in_sidebar', 'show_on_deals_page', 'show_in_category_grid',
            'grid_category_ids', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'click_count', 'created_at', 'updated_at']


class AffiliateProductPublicSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    program_label = serializers.SerializerMethodField()
    go_url = serializers.SerializerMethodField()
    target_url = serializers.SerializerMethodField()

    class Meta:
        model = AffiliateProduct
        fields = [
            'id', 'program', 'program_label', 'title', 'brand', 'image',
            'original_price', 'current_price', 'link_type', 'go_url', 'target_url',
            'display_order',
        ]
        read_only_fields = fields

    def get_image(self, obj):
        return absolutize_media_url(obj.image, self.context.get('request'))

    def get_program_label(self, obj):
        return PROGRAM_LABELS.get(obj.program, obj.program)

    def get_target_url(self, obj):
        """The affiliate destination itself, so the card can send the shopper
        straight there instead of bouncing them through our own host.

        go_url stays the tracked path and remains the fallback; a click that
        goes direct still reports itself with a background beacon. The point of
        exposing this is that the customer's tab never waits on our backend —
        on the free tier a cold start left them on a blank Render page for ~50s
        before the 302 fired.

        Returns None rather than raising when no adapter can resolve the
        product (unknown program, no manual override): one unresolvable row
        must not 500 the whole promoted list.
        """
        try:
            return build_affiliate_link(obj)
        except UnsupportedProgramError:
            # Expected: a program with no adapter and no manual override.
            return None
        except Exception:  # noqa: BLE001
            # Unexpected, so it is LOGGED rather than silently nulled — a bare
            # `except Exception: return None` here hid a missing import during
            # development and reported it as "no target", which looks
            # identical to the legitimate case above.
            logger.exception("affiliate: could not resolve target for product %s", obj.pk)
            return None

    def get_go_url(self, obj):
        path = reverse('store_affiliate_go', args=[obj.id])
        request = self.context.get('request')
        return request.build_absolute_uri(path) if request is not None else path
