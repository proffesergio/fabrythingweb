from rest_framework import serializers
from food.models import Restaurant, DeliveryZone, RestaurantHours, RestaurantZone


class _HoursSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantHours
        fields = ["weekday", "open_time", "close_time", "is_closed"]


class _AssignedZoneSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="zone.id")
    name = serializers.CharField(source="zone.name")

    class Meta:
        model = RestaurantZone
        fields = ["id", "name", "delivery_fee"]


class RestaurantAdminSerializer(serializers.ModelSerializer):
    hours = _HoursSerializer(many=True, read_only=True)
    zones = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = "__all__"

    def get_zones(self, obj):
        return _AssignedZoneSerializer(obj.restaurant_zones.all(), many=True).data


class DeliveryZoneAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryZone
        fields = "__all__"
