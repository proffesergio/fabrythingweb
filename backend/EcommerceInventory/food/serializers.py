from django.utils import timezone
from rest_framework import serializers
from food.models import (
    Restaurant, FoodCategory, FoodItem, FoodItemOptionGroup, FoodItemOption, DeliveryZone, Village,
)
from food.i18n import localized


class _LangMixin:
    @property
    def lang(self):
        return self.context.get("lang", "en")


class VillageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Village
        fields = ["id", "name", "name_bn"]


class DeliveryZoneSerializer(serializers.ModelSerializer):
    villages = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryZone
        fields = ["id", "name", "name_bn", "center_lat", "center_lng", "radius_km", "is_active", "villages"]

    def get_villages(self, obj):
        return VillageSerializer(
            [v for v in obj.villages.all() if v.is_active], many=True
        ).data


class FoodItemOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodItemOption
        fields = ["id", "name", "name_bn", "price_delta", "is_default", "display_order"]


class FoodItemOptionGroupSerializer(serializers.ModelSerializer):
    options = FoodItemOptionSerializer(many=True, read_only=True)

    class Meta:
        model = FoodItemOptionGroup
        fields = ["id", "name", "name_bn", "min_select", "max_select", "is_required", "options"]


class FoodItemSerializer(_LangMixin, serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    effective_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    option_groups = FoodItemOptionGroupSerializer(many=True, read_only=True)
    available_now = serializers.SerializerMethodField()

    class Meta:
        model = FoodItem
        fields = ["id", "name", "name_bn", "display_name", "slug", "description", "description_bn",
                  "image", "price", "discount_price", "effective_price", "prep_minutes",
                  "is_available", "is_veg", "is_featured", "tags", "available_from", "available_to",
                  "available_days", "available_now", "spice_level", "display_order", "option_groups"]

    def get_display_name(self, obj):
        return localized(obj, "name", self.lang)

    def get_available_now(self, obj):
        return obj.is_available_now(timezone.localtime())


class FoodCategorySerializer(_LangMixin, serializers.ModelSerializer):
    items = serializers.SerializerMethodField()

    class Meta:
        model = FoodCategory
        fields = ["id", "name", "name_bn", "display_order", "items"]

    def get_items(self, obj):
        # obj.items prefetched+filtered in the view; filter available in python to keep it 0-query
        items = [i for i in obj.items.all() if i.is_available]
        return FoodItemSerializer(items, many=True, context=self.context).data


class RestaurantListSerializer(_LangMixin, serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    # Set by PublicRestaurantListView when the caller sends lat/lng — straight-line
    # km from the customer's pin, used to order the "Nearest to you" row. Null when
    # the restaurant has no pickup coordinates or the caller sent no position.
    distance_km = serializers.SerializerMethodField()
    # True when this restaurant delivers to the zone the caller asked about. The
    # Browse page lists every restaurant, so cards need to say which ones you can
    # actually order from.
    delivers_to_zone = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = ["id", "name", "name_bn", "display_name", "slug", "logo", "cover_image",
                  "cuisine_type", "base_delivery_fee", "avg_prep_minutes", "min_order_amount",
                  "is_open", "is_accepting_orders", "status",
                  "pickup_lat", "pickup_lng", "distance_km", "delivers_to_zone"]

    def get_display_name(self, obj):
        return localized(obj, "name", self.lang)

    def get_distance_km(self, obj):
        # Annotated in the view (a plain float attribute), not a DB field.
        value = getattr(obj, "distance_km", None)
        return round(value, 2) if value is not None else None

    def get_delivers_to_zone(self, obj):
        return getattr(obj, "delivers_to_zone", None)


class RestaurantDetailSerializer(RestaurantListSerializer):
    categories = serializers.SerializerMethodField()

    class Meta(RestaurantListSerializer.Meta):
        fields = RestaurantListSerializer.Meta.fields + ["description", "description_bn",
                 "address", "phone", "pickup_lat", "pickup_lng", "categories"]

    def get_categories(self, obj):
        cats = [c for c in obj.categories.all() if c.is_active]
        return FoodCategorySerializer(cats, many=True, context=self.context).data
