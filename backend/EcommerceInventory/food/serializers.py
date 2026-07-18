from rest_framework import serializers
from food.models import (
    Restaurant, FoodCategory, FoodItem, FoodItemOptionGroup, FoodItemOption, DeliveryZone,
)
from food.i18n import localized


class _LangMixin:
    @property
    def lang(self):
        return self.context.get("lang", "en")


class DeliveryZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryZone
        fields = ["id", "name", "name_bn", "center_lat", "center_lng", "radius_km", "is_active"]


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

    class Meta:
        model = FoodItem
        fields = ["id", "name", "name_bn", "display_name", "slug", "description", "description_bn",
                  "image", "price", "discount_price", "effective_price", "prep_minutes",
                  "is_available", "is_veg", "spice_level", "display_order", "option_groups"]

    def get_display_name(self, obj):
        return localized(obj, "name", self.lang)


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
    name = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = ["id", "name", "name_bn", "display_name", "slug", "logo", "cover_image",
                  "cuisine_type", "base_delivery_fee", "avg_prep_minutes", "min_order_amount",
                  "is_open", "status"]

    def get_display_name(self, obj):
        return localized(obj, "name", self.lang)

    def get_name(self, obj):
        return localized(obj, "name", self.lang)


class RestaurantDetailSerializer(RestaurantListSerializer):
    categories = serializers.SerializerMethodField()

    class Meta(RestaurantListSerializer.Meta):
        fields = RestaurantListSerializer.Meta.fields + ["description", "description_bn",
                 "address", "phone", "pickup_lat", "pickup_lng", "categories"]

    def get_categories(self, obj):
        cats = [c for c in obj.categories.all() if c.is_active]
        return FoodCategorySerializer(cats, many=True, context=self.context).data
