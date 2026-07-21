from rest_framework import serializers
from food.models import FoodCategory, FoodItem, FoodItemOptionGroup, FoodItemOption


class AdminCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodCategory
        fields = ["id", "restaurant", "name", "name_bn", "display_order", "is_active"]


class AdminItemSerializer(serializers.ModelSerializer):
    # Slug is auto-generated server-side from name (unique per restaurant).
    slug = serializers.SlugField(read_only=True)

    # Curated tag keys, mirrored by TAG_OPTIONS in FoodMenuManager.js.
    ALLOWED_TAGS = ["spicy", "new", "popular", "bestseller", "veg"]
    # The admin dialog sends "" for optional fields the user never touched.
    # DRF rejects "" for Decimal/Integer/Time, so normalise it to None (unset)
    # before validation. None is also how the UI clears an existing value.
    BLANKABLE = ["discount_price", "prep_minutes", "available_from", "available_to"]

    class Meta:
        model = FoodItem
        fields = ["id", "restaurant", "category_id", "name", "name_bn", "slug", "description",
                  "description_bn", "image", "price", "discount_price", "prep_minutes",
                  "is_available", "is_veg", "is_featured", "tags", "available_from", "available_to",
                  "available_days", "spice_level", "display_order"]
        extra_kwargs = {
            "discount_price": {"allow_null": True, "required": False},
            "prep_minutes": {"allow_null": True, "required": False},
            "available_from": {"allow_null": True, "required": False},
            "available_to": {"allow_null": True, "required": False},
        }

    def to_internal_value(self, data):
        if hasattr(data, "dict"):
            data = data.dict()
        else:
            data = dict(data)
        for field in self.BLANKABLE:
            if data.get(field) == "":
                data[field] = None
        return super().to_internal_value(data)

    def validate_tags(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Tags must be a list.")
        unknown = [t for t in value if t not in self.ALLOWED_TAGS]
        if unknown:
            raise serializers.ValidationError(
                f"Unknown tag(s): {', '.join(map(str, unknown))}. "
                f"Allowed: {', '.join(self.ALLOWED_TAGS)}."
            )
        return value

    def validate_available_days(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Available days must be a list.")
        days = []
        for raw in value:
            try:
                day = int(raw)
            except (TypeError, ValueError):
                raise serializers.ValidationError(f"'{raw}' is not a weekday number.")
            if not 0 <= day <= 6:
                raise serializers.ValidationError("Weekdays must be between 0 (Mon) and 6 (Sun).")
            days.append(day)
        return days


class AdminOptionGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodItemOptionGroup
        fields = ["id", "item", "name", "name_bn", "min_select", "max_select", "is_required"]


class AdminOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodItemOption
        fields = ["id", "group", "name", "name_bn", "price_delta", "is_default", "display_order"]
