from rest_framework import serializers
from food.models import FoodCategory, FoodItem, FoodItemOptionGroup, FoodItemOption


class AdminCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodCategory
        fields = ["id", "restaurant", "name", "name_bn", "display_order", "is_active"]


class AdminItemSerializer(serializers.ModelSerializer):
    # Slug is auto-generated server-side from name (unique per restaurant).
    slug = serializers.SlugField(read_only=True)

    class Meta:
        model = FoodItem
        fields = ["id", "restaurant", "category_id", "name", "name_bn", "slug", "description",
                  "description_bn", "image", "price", "discount_price", "prep_minutes",
                  "is_available", "is_veg", "is_featured", "spice_level", "display_order"]


class AdminOptionGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodItemOptionGroup
        fields = ["id", "item", "name", "name_bn", "min_select", "max_select", "is_required"]


class AdminOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodItemOption
        fields = ["id", "group", "name", "name_bn", "price_delta", "is_default", "display_order"]
