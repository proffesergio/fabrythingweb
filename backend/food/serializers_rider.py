"""Order payload for the rider dashboard.

Extends the shared FoodOrderSerializer with what a rider on a motorbike needs
and nobody else does: where to pick up, who to call at each end, what to check
in the bag, and how much cash to collect at the door.
"""
from decimal import Decimal

from rest_framework import serializers

from food.models import FoodOrder
from food.serializers_orders import FoodOrderSerializer


class RiderOrderSerializer(FoodOrderSerializer):
    pickup_lat = serializers.DecimalField(source="restaurant.pickup_lat", max_digits=9,
                                          decimal_places=6, read_only=True)
    pickup_lng = serializers.DecimalField(source="restaurant.pickup_lng", max_digits=9,
                                          decimal_places=6, read_only=True)
    restaurant_phone = serializers.CharField(source="restaurant.phone", read_only=True)
    restaurant_address = serializers.CharField(source="restaurant.address", read_only=True)
    cash_to_collect = serializers.SerializerMethodField()

    class Meta(FoodOrderSerializer.Meta):
        model = FoodOrder
        fields = FoodOrderSerializer.Meta.fields + [
            "pickup_lat", "pickup_lng", "restaurant_phone", "restaurant_address",
            "notes", "cash_to_collect",
        ]

    def get_cash_to_collect(self, obj):
        unpaid_cod = obj.payment_method == "COD" and obj.payment_status != "COLLECTED"
        return str(obj.total if unpaid_cod else Decimal("0.00"))
