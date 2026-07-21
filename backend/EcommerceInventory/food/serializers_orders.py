from rest_framework import serializers
from food.models import FoodOrder, FoodOrderItem


class FoodOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodOrderItem
        fields = ["id", "item_name", "unit_price", "quantity", "selected_options", "line_total"]


class FoodOrderSerializer(serializers.ModelSerializer):
    items = FoodOrderItemSerializer(many=True, read_only=True)
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    restaurant_slug = serializers.CharField(source="restaurant.slug", read_only=True)
    rider_name = serializers.CharField(source="rider.name", read_only=True, default=None)
    rider_phone = serializers.CharField(source="rider.phone", read_only=True, default=None)
    village_name = serializers.CharField(source="village.name", read_only=True, default=None)
    zone_name = serializers.CharField(source="zone.name", read_only=True, default=None)

    class Meta:
        model = FoodOrder
        fields = ["id", "order_code", "status", "restaurant_name", "restaurant_slug",
                  "guest_name", "guest_phone", "delivery_address", "village_name", "zone_name",
                  "delivery_lat", "delivery_lng", "subtotal", "discount",
                  "coupon_code", "delivery_fee", "tip", "total", "eta_minutes", "payment_method",
                  "payment_status", "rider_name", "rider_phone", "created_at", "items"]
