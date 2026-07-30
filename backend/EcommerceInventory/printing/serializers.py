from decimal import Decimal

from rest_framework import serializers

from printing.models import (
    PrintArea, PrintablePreset, PrintPricingConfig, PrintProof, PrintRequest, PrintRosterLine,
)

MAX_REFERENCE_IMAGES = 10


class PrintAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrintArea
        fields = ["id", "name", "price", "is_active", "display_order"]
        read_only_fields = ["id"]


class PrintablePresetSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="product.id", read_only=True, allow_null=True)
    product_name = serializers.CharField(source="product.name", read_only=True, allow_null=True, default=None)

    class Meta:
        model = PrintablePreset
        fields = [
            "id", "name", "base_price", "available_colors", "available_sizes",
            "is_active", "display_order", "product_id", "product_name",
        ]
        read_only_fields = ["id", "product_id", "product_name"]


class PrintablePresetWriteSerializer(serializers.ModelSerializer):
    """Staff CRUD -- ``product`` is a plain writable FK id here (unlike the
    read-only ``product_id``/``product_name`` pair on PrintablePresetSerializer)."""

    class Meta:
        model = PrintablePreset
        fields = [
            "id", "product", "name", "base_price", "available_colors",
            "available_sizes", "is_active", "display_order",
        ]
        read_only_fields = ["id"]


class PrintRosterLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrintRosterLine
        fields = ["id", "print_request", "player_name", "number", "size", "quantity", "created_at"]
        read_only_fields = ["id", "print_request", "created_at"]


class PrintProofSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrintProof
        fields = [
            "id", "print_request", "image", "version", "note", "decision",
            "customer_feedback", "decided_at", "created_at",
        ]
        read_only_fields = fields


class ProofDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=[PrintProof.Decision.APPROVED, PrintProof.Decision.REVISION_REQUESTED])
    feedback = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs["decision"] == PrintProof.Decision.REVISION_REQUESTED and not attrs.get("feedback", "").strip():
            raise serializers.ValidationError({"feedback": ["Feedback is required when requesting a revision."]})
        return attrs


class PrintRequestCreateSerializer(serializers.Serializer):
    """Customer submission. ``roster_lines`` is optional and only meaningful
    for team/jersey orders -- a plain single-item request omits it."""

    product = serializers.IntegerField(required=False, allow_null=True)
    preset = serializers.IntegerField(required=False, allow_null=True)
    color = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    size = serializers.ChoiceField(choices=PrintRequest._meta.get_field("size").choices, required=False, allow_blank=True, default="")
    quantity = serializers.IntegerField(min_value=1, default=1)
    brief = serializers.CharField(allow_blank=False, trim_whitespace=True)
    reference_images = serializers.ListField(
        child=serializers.URLField(), required=False, default=list, max_length=MAX_REFERENCE_IMAGES,
    )
    print_areas = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    roster_lines = serializers.ListField(required=False, default=list)

    def validate_product(self, value):
        if value is None:
            return None
        from catalog.models import Products

        if not Products.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Unknown product.")
        return value

    def validate_preset(self, value):
        if value is None:
            return None
        if not PrintablePreset.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError("Unknown or inactive preset.")
        return value

    def validate_print_areas(self, value):
        found = set(PrintArea.objects.filter(pk__in=value, is_active=True).values_list("id", flat=True))
        missing = set(value) - found
        if missing:
            raise serializers.ValidationError(f"Unknown or inactive print area id(s): {sorted(missing)}.")
        return value

    def validate_roster_lines(self, value):
        cleaned = []
        for i, line in enumerate(value):
            if not isinstance(line, dict) or not line.get("player_name"):
                raise serializers.ValidationError(f"Roster line {i}: player_name is required.")
            cleaned.append({
                "player_name": str(line["player_name"])[:120],
                "number": str(line.get("number", ""))[:10],
                "size": line.get("size", ""),
                "quantity": max(1, int(line.get("quantity", 1))),
            })
        return cleaned


class QuoteRequestSerializer(serializers.Serializer):
    """Live price preview before submitting -- same computation
    printing.services.compute_quote runs at approval time, so the estimate
    a customer sees on the form can never disagree with what staff quotes."""

    preset = serializers.IntegerField(required=False, allow_null=True)
    print_areas = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    quantity = serializers.IntegerField(min_value=1, default=1)


class PrintRequestListSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True, allow_null=True, default=None)
    preset_name = serializers.CharField(source="preset.name", read_only=True, allow_null=True, default=None)
    print_area_ids = serializers.PrimaryKeyRelatedField(source="print_areas", many=True, read_only=True)

    class Meta:
        model = PrintRequest
        fields = [
            "id", "status", "product", "product_name", "preset", "preset_name",
            "print_area_ids", "color", "size", "quantity", "brief", "reference_images",
            "quoted_unit_price", "quoted_total_price", "agreed_unit_price", "agreed_total_price",
            "approved_at", "chat_thread", "created_at", "updated_at",
        ]
        read_only_fields = fields


class PrintRequestDetailSerializer(PrintRequestListSerializer):
    proofs = PrintProofSerializer(many=True, read_only=True)
    roster_lines = PrintRosterLineSerializer(many=True, read_only=True)
    quote = serializers.SerializerMethodField()

    class Meta(PrintRequestListSerializer.Meta):
        fields = PrintRequestListSerializer.Meta.fields + ["proofs", "roster_lines", "quote"]
        read_only_fields = fields

    def get_quote(self, obj):
        from printing.services import compute_quote

        if obj.agreed_unit_price is not None:
            return None  # price is locked in; agreed_unit_price/agreed_total_price are authoritative
        quote = compute_quote(obj)
        return {k: str(v) for k, v in quote.items()}


class AdminPrintRequestListSerializer(PrintRequestListSerializer):
    customer_username = serializers.CharField(source="customer.username", read_only=True, default=None)
    customer_email = serializers.CharField(source="customer.email", read_only=True, default=None)

    class Meta(PrintRequestListSerializer.Meta):
        fields = PrintRequestListSerializer.Meta.fields + [
            "customer", "customer_username", "customer_email", "staff_notes",
        ]
        read_only_fields = fields


class AdminPrintRequestDetailSerializer(AdminPrintRequestListSerializer, PrintRequestDetailSerializer):
    class Meta(AdminPrintRequestListSerializer.Meta):
        fields = list(dict.fromkeys(
            AdminPrintRequestListSerializer.Meta.fields + PrintRequestDetailSerializer.Meta.fields
        ))
        read_only_fields = fields


class AdminProofCreateSerializer(serializers.Serializer):
    image = serializers.URLField()
    note = serializers.CharField(required=False, allow_blank=True, default="")


class AdminPriceSerializer(serializers.Serializer):
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0"))
    total_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, allow_null=True,
    )


class AdminStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=PrintRequest.Status.choices)


class PrintPricingConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrintPricingConfig
        fields = ["id", "quantity_tiers", "updated_at"]
        read_only_fields = ["id", "updated_at"]
