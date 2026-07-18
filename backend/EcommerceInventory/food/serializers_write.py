from rest_framework import serializers
from food.models import FoodCategory, FoodItem, FoodItemOptionGroup, FoodItemOption


class FoodCategoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodCategory
        fields = ["id", "name", "name_bn", "display_order", "is_active"]


class FoodItemWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodItem
        fields = ["id", "category_id", "name", "name_bn", "slug", "description", "description_bn",
                  "image", "price", "discount_price", "prep_minutes", "is_available",
                  "is_veg", "spice_level", "display_order"]
