from rest_framework import serializers
from food.models import Restaurant, DeliveryZone


class RestaurantAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = "__all__"


class DeliveryZoneAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryZone
        fields = "__all__"
