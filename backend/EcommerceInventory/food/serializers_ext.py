from rest_framework import serializers
from food.models import Coupon, Rider, Notification, PaymentTransaction


class CouponSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True, default=None)

    class Meta:
        model = Coupon
        fields = ["id", "code", "restaurant", "restaurant_name", "discount_type", "discount_value",
                  "min_order_amount", "max_discount", "valid_from", "valid_until", "usage_limit",
                  "used_count", "is_active", "created_at"]
        read_only_fields = ["used_count"]


class RiderSerializer(serializers.ModelSerializer):
    # The admin panel shows these so an admin can hand a rider working
    # credentials (there is no self-serve rider signup or password reset).
    # Never expose the password hash — only the identifier to log in with.
    username = serializers.CharField(source="user.username", read_only=True, default=None)
    email = serializers.CharField(source="user.email", read_only=True, default=None)
    is_online = serializers.BooleanField(read_only=True)

    class Meta:
        model = Rider
        fields = ["id", "rider_code", "name", "phone", "vehicle_type", "vehicle_number",
                  "is_available", "is_verified", "total_deliveries", "created_at",
                  "current_lat", "current_lng", "last_seen_at",
                  "username", "email", "is_online"]
        read_only_fields = ["rider_code", "total_deliveries",
                            "current_lat", "current_lng", "last_seen_at"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "body", "order_code", "is_read", "created_at"]


class PaymentSerializer(serializers.ModelSerializer):
    order_code = serializers.CharField(source="order.order_code", read_only=True)

    class Meta:
        model = PaymentTransaction
        fields = ["id", "order_code", "method", "amount", "status", "provider_ref", "created_at"]
