from rest_framework import serializers

from food.models import OrderSettlement, Village, DeliveryZone


class SettlementSerializer(serializers.ModelSerializer):
    order_code = serializers.CharField(source="order.order_code", read_only=True)
    order_id = serializers.IntegerField(source="order.id", read_only=True)
    order_total = serializers.DecimalField(source="order.total", max_digits=10,
                                           decimal_places=2, read_only=True)
    payment_method = serializers.CharField(source="order.payment_method", read_only=True)
    restaurant_name = serializers.CharField(source="order.restaurant.name", read_only=True)
    customer_name = serializers.CharField(source="order.guest_name", read_only=True)
    customer_phone = serializers.CharField(source="order.guest_phone", read_only=True)
    delivered_at = serializers.DateTimeField(source="created_at", read_only=True)
    is_fully_settled = serializers.BooleanField(read_only=True)

    class Meta:
        model = OrderSettlement
        fields = [
            "id", "order_id", "order_code", "order_total", "payment_method",
            "restaurant_name", "customer_name", "customer_phone", "delivered_at",
            # Who delivered it.
            "rider", "rider_name",
            # The money split, all derived from order_total.
            "commission_rate", "food_net", "delivery_fee", "tip",
            "commission_amount", "restaurant_payout", "rider_base_pay",
            "rider_payout", "platform_revenue",
            # Settlement state, one per money movement.
            "customer_payment_status", "rider_cash_status",
            "rider_payout_status", "restaurant_payout_status",
            "customer_payment_at", "rider_cash_at",
            "rider_payout_at", "restaurant_payout_at",
            "is_fully_settled", "notes",
        ]
        read_only_fields = [f for f in fields if f != "notes"]


class VillageAdminSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source="zone.name", read_only=True)
    zone_name_bn = serializers.CharField(source="zone.name_bn", read_only=True)
    # What the customer-facing UI should render: Bangla when we have it,
    # English otherwise (see CLAUDE.md — Bangla default, English fallback).
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Village
        fields = ["id", "zone", "zone_name", "zone_name_bn", "name", "name_bn",
                  "display_name", "is_active", "created_at"]

    def get_display_name(self, obj):
        return obj.name_bn or obj.name


class ZoneWithVillagesSerializer(serializers.ModelSerializer):
    villages = VillageAdminSerializer(many=True, read_only=True)
    village_count = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryZone
        fields = ["id", "name", "name_bn", "display_name", "center_lat", "center_lng",
                  "radius_km", "is_active", "villages", "village_count", "created_at"]

    def get_display_name(self, obj):
        return obj.name_bn or obj.name

    def get_village_count(self, obj):
        return obj.villages.count()
