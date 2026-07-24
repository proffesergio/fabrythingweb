from rest_framework import serializers
from food.models import FoodOrder, FoodOrderItem

# The rider's live pin is shown to the customer only while the food is actually
# moving. Before that it would leak a rider's whereabouts with no delivery to
# justify it, and after DELIVERED it is stale and equally unjustified.
LIVE_TRACKING_STATUSES = {FoodOrder.Status.OUT_FOR_DELIVERY}


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
    # Live pin — null unless the order is OUT_FOR_DELIVERY (see LIVE_TRACKING_STATUSES).
    rider_lat = serializers.SerializerMethodField()
    rider_lng = serializers.SerializerMethodField()
    rider_last_seen_at = serializers.SerializerMethodField()
    restaurant_lat = serializers.DecimalField(source="restaurant.pickup_lat", max_digits=9,
                                              decimal_places=6, read_only=True, default=None)
    restaurant_lng = serializers.DecimalField(source="restaurant.pickup_lng", max_digits=9,
                                              decimal_places=6, read_only=True, default=None)

    class Meta:
        model = FoodOrder
        fields = ["id", "order_code", "status", "restaurant_name", "restaurant_slug",
                  "guest_name", "guest_phone", "delivery_address", "village_name", "zone_name",
                  "delivery_lat", "delivery_lng", "subtotal", "discount",
                  "coupon_code", "delivery_fee", "tip", "total", "eta_minutes", "payment_method",
                  "payment_status", "rider_name", "rider_phone",
                  "rider_lat", "rider_lng", "rider_last_seen_at",
                  "restaurant_lat", "restaurant_lng", "created_at", "items"]

    def _live_rider(self, obj):
        if obj.status not in LIVE_TRACKING_STATUSES:
            return None
        return obj.rider

    def _sharing_rider(self, obj):
        # Position is withheld unless the rider has actively opted in, on top
        # of the existing order-status gate (see _live_rider).
        rider = self._live_rider(obj)
        return rider if rider and rider.is_sharing_location else None

    def get_rider_lat(self, obj):
        rider = self._sharing_rider(obj)
        return str(rider.current_lat) if rider and rider.current_lat is not None else None

    def get_rider_lng(self, obj):
        rider = self._sharing_rider(obj)
        return str(rider.current_lng) if rider and rider.current_lng is not None else None

    def get_rider_last_seen_at(self, obj):
        rider = self._live_rider(obj)
        return rider.last_seen_at if rider and rider.last_seen_at else None
