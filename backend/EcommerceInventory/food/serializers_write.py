from rest_framework import serializers
from food.models import FoodCategory, FoodItem, Restaurant


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


class VendorRestaurantSerializer(serializers.ModelSerializer):
    """Self-service profile editor for the owning restaurant. Deliberately excludes
    the owner/commission/status/slug fields — those are platform-controlled and must
    never be writable by the vendor themselves (see food/views_vendor.py::VendorRestaurantView)."""

    class Meta:
        model = Restaurant
        fields = [
            "id", "name", "name_bn", "slug", "description", "description_bn",
            "logo", "cover_image", "cuisine_type", "phone", "address",
            "pickup_lat", "pickup_lng", "commission_percentage", "base_delivery_fee",
            "avg_prep_minutes", "min_order_amount", "status", "is_open",
        ]
        read_only_fields = ["id", "slug", "commission_percentage", "status"]
