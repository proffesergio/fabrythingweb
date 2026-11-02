"""Admin menu CRUD — categories/items/options for ANY restaurant (chosen via ?restaurant=/body).

Mirrors the vendor viewsets, but the restaurant is supplied by the admin request instead of
being derived from request.user.restaurant, and the gate is IsPlatformAdmin.
"""
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from food.models import FoodCategory, FoodItem, FoodItemOptionGroup, FoodItemOption
from food.permissions import IsPlatformAdmin
from food.views_vendor import EnvelopeModelViewSetMixin, _unique_item_slug
from food.serializers_admin_menu import (
    AdminCategorySerializer, AdminItemSerializer, AdminOptionGroupSerializer, AdminOptionSerializer,
)


class _AdminMenuBase(EnvelopeModelViewSetMixin, ModelViewSet):
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    pagination_class = None


class AdminCategoryViewSet(_AdminMenuBase):
    serializer_class = AdminCategorySerializer
    entity_name = "Category"

    def get_queryset(self):
        qs = FoodCategory.objects.all().order_by("display_order")
        r = self.request.GET.get("restaurant")
        return qs.filter(restaurant_id=r) if r else qs


class AdminItemViewSet(_AdminMenuBase):
    serializer_class = AdminItemSerializer
    entity_name = "Item"

    def get_queryset(self):
        qs = FoodItem.objects.all().order_by("display_order")
        r = self.request.GET.get("restaurant")
        return qs.filter(restaurant_id=r) if r else qs

    def _check_category(self, restaurant, category):
        if category and restaurant and category.restaurant_id != restaurant.id:
            raise PermissionDenied("Category does not belong to that restaurant.")

    def perform_create(self, serializer):
        restaurant = serializer.validated_data.get("restaurant")
        self._check_category(restaurant, serializer.validated_data.get("category_id"))
        slug = _unique_item_slug(restaurant, serializer.validated_data.get("name"))
        serializer.save(slug=slug)

    def perform_update(self, serializer):
        restaurant = serializer.validated_data.get("restaurant") or serializer.instance.restaurant
        self._check_category(restaurant, serializer.validated_data.get("category_id"))
        serializer.save()


class AdminOptionGroupViewSet(_AdminMenuBase):
    serializer_class = AdminOptionGroupSerializer
    entity_name = "Option group"

    def get_queryset(self):
        qs = FoodItemOptionGroup.objects.all()
        item = self.request.GET.get("item")
        return qs.filter(item_id=item) if item else qs


class AdminOptionViewSet(_AdminMenuBase):
    serializer_class = AdminOptionSerializer
    entity_name = "Option"

    def get_queryset(self):
        qs = FoodItemOption.objects.all().order_by("display_order")
        g = self.request.GET.get("group")
        return qs.filter(group_id=g) if g else qs
