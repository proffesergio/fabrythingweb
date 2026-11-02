"""Serializers for the web-to-press engine. Explicit interfaces per the spec's
code-generation strategy (typed configs in, priced breakdowns out)."""
from decimal import Decimal

from rest_framework import serializers

from printing.fields import MediaURLField
from printing.models import (
    CorporateAccount, FinishingOption, PaperStock, PressOrder, PressProduct,
    PressShippingRate, PressShopConfig, PressSizePreset, Quotation,
)
from printing.services_press import DEFAULT_ALLOWED_EXTENSIONS

SIDES_CHOICES = ["4/0", "4/4"]
PAYMENT_METHODS = [c[0] for c in PressOrder.PAYMENT_METHODS]
SHIPPING_ZONES = ["INSIDE_DHAKA_HOME", "HUB_PICKUP", "OUTSIDE_DHAKA"]


class PressSizePresetSerializer(serializers.ModelSerializer):
    class Meta:
        model = PressSizePreset
        fields = ["id", "name", "width", "height", "unit", "is_active", "display_order"]
        read_only_fields = ["id"]


class PressProductSerializer(serializers.ModelSerializer):
    size_presets = PressSizePresetSerializer(many=True, read_only=True)
    effective_margin = serializers.SerializerMethodField()
    from_price_bdt = serializers.SerializerMethodField()

    class Meta:
        model = PressProduct
        fields = [
            "id", "name", "slug", "category", "description", "image",
            "base_setup_cost", "per_unit_material_cost", "per_sq_inch_rate",
            "margin_factor", "effective_margin", "min_qty", "allow_custom_size",
            "weight_per_unit_kg", "is_active", "display_order",
            "size_presets", "from_price_bdt",
        ]
        read_only_fields = fields

    def get_effective_margin(self, obj):
        return str(obj.effective_margin())

    def get_from_price_bdt(self, obj):
        from printing.services_press import compute_press_quote

        try:
            preset = obj.size_presets.filter(is_active=True).order_by("display_order").first()
            if preset:
                q = compute_press_quote(
                    product=obj, width=preset.width, height=preset.height,
                    unit=preset.unit, quantity=max(obj.min_qty, 1),
                )
            else:
                q = compute_press_quote(product=obj, width=1, height=1, quantity=max(obj.min_qty, 1))
            return str(q["total_bdt"])
        except Exception:
            return str(obj.base_setup_cost)


class PressProductWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PressProduct
        fields = [
            "id", "name", "slug", "category", "description", "image",
            "base_setup_cost", "per_unit_material_cost", "per_sq_inch_rate",
            "margin_factor", "quantity_tiers", "min_qty", "allow_custom_size",
            "allowed_extensions", "weight_per_unit_kg", "is_active", "display_order",
        ]
        read_only_fields = ["id"]


class PaperStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaperStock
        fields = ["id", "name", "gsm", "multiplier", "flat_addon_per_unit", "is_active", "display_order"]
        read_only_fields = ["id"]


class FinishingOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinishingOption
        fields = ["id", "kind", "name", "price", "per_unit", "is_active", "display_order"]
        read_only_fields = ["id"]


class PressShippingRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PressShippingRate
        fields = ["id", "zone", "courier", "base_fee", "per_kg_fee", "is_active"]
        read_only_fields = ["id"]


class PressShopConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = PressShopConfig
        fields = ["id", "usd_rate", "default_margin_factor", "max_upload_mb", "currency_default", "shipping_matrix", "updated_at"]
        read_only_fields = ["id", "updated_at"]


class PressQuoteRequestSerializer(serializers.Serializer):
    """Reactive calculator input — mirrors the storefront usePressPricing hook."""

    product = serializers.IntegerField()
    width = serializers.DecimalField(max_digits=8, decimal_places=2)
    height = serializers.DecimalField(max_digits=8, decimal_places=2)
    unit = serializers.ChoiceField(choices=["in", "ft", "mm"], default="in")
    paper_stock = serializers.IntegerField(required=False, allow_null=True, default=None)
    finishing_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    quantity = serializers.IntegerField(min_value=1, default=1)
    sides = serializers.ChoiceField(choices=SIDES_CHOICES, default="4/0")
    currency = serializers.ChoiceField(choices=["BDT", "USD"], default="BDT")
    shipping_zone = serializers.ChoiceField(choices=SHIPPING_ZONES, default="INSIDE_DHAKA_HOME")
    shipping_courier = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_product(self, value):
        if not PressProduct.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError("Unknown or inactive product.")
        return value

    def validate(self, attrs):
        if attrs["width"] <= 0 or attrs["height"] <= 0:
            raise serializers.ValidationError("Width and height must be positive.")
        product = PressProduct.objects.filter(pk=attrs["product"]).first()
        if product and attrs["quantity"] < product.min_qty:
            raise serializers.ValidationError(f"Minimum order for {product.name} is {product.min_qty} pcs.")
        return attrs


class ArtworkFileSerializer(serializers.Serializer):
    url = MediaURLField()
    name = serializers.CharField(required=False, allow_blank=True, default="")
    size = serializers.IntegerField(required=False, default=0)
    content_type = serializers.CharField(required=False, allow_blank=True, default="")
    width_px = serializers.IntegerField(required=False, allow_null=True, default=None)
    height_px = serializers.IntegerField(required=False, allow_null=True, default=None)


class PressCheckoutSerializer(PressQuoteRequestSerializer):
    """Checkout = quote input + payment + shipping address + artwork."""

    payment_method = serializers.ChoiceField(choices=PAYMENT_METHODS, default="SSLCOMMERZ")
    shipping_address = serializers.DictField(required=False, default=dict)
    artwork_files = ArtworkFileSerializer(many=True, required=False, default=list)
    size_name = serializers.CharField(required=False, allow_blank=True, default="")
    po_number = serializers.CharField(required=False, allow_blank=True, default="")
    is_corporate = serializers.BooleanField(required=False, default=False)
    quotation_id = serializers.IntegerField(required=False, allow_null=True, default=None)

    def validate_artwork_files(self, value):
        if len(value) > 10:
            raise serializers.ValidationError("At most 10 artwork files per order.")
        return value


class PressOrderListSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True, default=None)
    paper_name = serializers.CharField(source="paper_stock.name", read_only=True, default=None)
    finishing_names = serializers.SerializerMethodField()

    class Meta:
        model = PressOrder
        fields = [
            "id", "status", "product", "product_name", "paper_stock", "paper_name",
            "finishing_names", "size_name", "width", "height", "size_unit", "sides",
            "quantity", "price_breakdown", "total_bdt", "currency", "total_charged",
            "payment_method", "payment_status", "payment_txn_id",
            "shipping_zone", "shipping_courier", "shipping_fee_bdt",
            "artwork_validation", "is_corporate", "po_number",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_finishing_names(self, obj):
        return [f.name for f in obj.finishing_options.all()]


class PressOrderDetailSerializer(PressOrderListSerializer):
    artwork_files = serializers.JSONField(read_only=True)
    shipping_address = serializers.JSONField(read_only=True)

    class Meta(PressOrderListSerializer.Meta):
        fields = PressOrderListSerializer.Meta.fields + [
            "artwork_files", "shipping_address",
        ]
        read_only_fields = fields


class AdminPressOrderListSerializer(PressOrderListSerializer):
    customer_username = serializers.CharField(source="customer.username", read_only=True, default=None)
    customer_email = serializers.CharField(source="customer.email", read_only=True, default=None)

    class Meta(PressOrderListSerializer.Meta):
        fields = PressOrderListSerializer.Meta.fields + [
            "customer", "customer_username", "customer_email", "staff_notes",
        ]
        read_only_fields = fields


class AdminPressOrderDetailSerializer(AdminPressOrderListSerializer, PressOrderDetailSerializer):
    class Meta(AdminPressOrderListSerializer.Meta):
        fields = list(dict.fromkeys(
            AdminPressOrderListSerializer.Meta.fields + PressOrderDetailSerializer.Meta.fields
        ))
        read_only_fields = fields


class AdminPressStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=PressOrder.Status.choices)


class AdminPaymentSerializer(serializers.Serializer):
    payment_status = serializers.ChoiceField(choices=[c[0] for c in PressOrder.PAYMENT_STATUS])
    payment_txn_id = serializers.CharField(required=False, allow_blank=True, default="")


class CorporateAccountSerializer(serializers.ModelSerializer):
    customer_username = serializers.CharField(source="customer.username", read_only=True, default=None)

    class Meta:
        model = CorporateAccount
        fields = [
            "id", "customer", "customer_username", "company_name", "contact_phone",
            "billing_address", "credit_limit_bdt", "ledger_balance_bdt",
            "trusted_for_partial", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "customer_username", "ledger_balance_bdt", "created_at", "updated_at"]


class QuotationSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True, default=None)

    class Meta:
        model = Quotation
        fields = [
            "id", "product", "product_name", "config_snapshot", "price_breakdown",
            "total_bdt", "currency", "po_number", "status", "press_order",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "product_name", "price_breakdown", "total_bdt", "press_order", "created_at", "updated_at"]


class QuotationCreateSerializer(PressQuoteRequestSerializer):
    po_number = serializers.CharField(required=False, allow_blank=True, default="")
