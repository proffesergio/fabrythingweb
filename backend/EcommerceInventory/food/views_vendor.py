from django.utils.text import slugify
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.helpers import renderResponse
from food.models import FoodCategory, FoodItem
from food.permissions import IsRestaurantOwner
from food.serializers_write import FoodCategoryWriteSerializer, FoodItemWriteSerializer, VendorRestaurantSerializer


def _unique_item_slug(restaurant, name):
    """Generate a slug for a new item that is unique within the restaurant,
    satisfying FoodItem's (restaurant, slug) UniqueConstraint. Vendors never
    supply a slug themselves (see FoodItemWriteSerializer.slug, read_only)."""
    base = slugify(name) or "item"
    slug = base
    i = 2
    while FoodItem.objects.filter(restaurant=restaurant, slug=slug).exists():
        slug = f"{base}-{i}"
        i += 1
    return slug


class EnvelopeModelViewSetMixin:
    """Wraps DRF's default ModelViewSet actions in this project's standard
    ``{"data": ..., "message": ...}`` response envelope (see core.helpers.renderResponse),
    matching every other endpoint in this codebase (storefront + public food API).
    """

    entity_name = "Object"
    # This project has no DEFAULT_AUTHENTICATION_CLASSES configured in REST_FRAMEWORK
    # settings (see accounts/storefront controllers) — every authenticated view sets
    # this explicitly, or request.user is AnonymousUser regardless of the bearer token.
    authentication_classes = [JWTAuthentication]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return renderResponse(data=serializer.data, message=f"{self.entity_name} retrieved")

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return renderResponse(data=serializer.data, message=f"{self.entity_name} retrieved")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message="Validation error", status=400)
        self.perform_create(serializer)
        return renderResponse(data=serializer.data, message=f"{self.entity_name} created", status=201)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message="Validation error", status=400)
        self.perform_update(serializer)
        return renderResponse(data=serializer.data, message=f"{self.entity_name} updated")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return renderResponse(data=None, message=f"{self.entity_name} deleted")


class VendorCategoryViewSet(EnvelopeModelViewSetMixin, ModelViewSet):
    permission_classes = [IsAuthenticated, IsRestaurantOwner]
    serializer_class = FoodCategoryWriteSerializer
    pagination_class = None
    entity_name = "Category"

    def get_queryset(self):
        return FoodCategory.objects.filter(restaurant=self.request.user.restaurant).order_by("display_order")

    def perform_create(self, serializer):
        serializer.save(restaurant=self.request.user.restaurant)


class VendorItemViewSet(EnvelopeModelViewSetMixin, ModelViewSet):
    permission_classes = [IsAuthenticated, IsRestaurantOwner]
    serializer_class = FoodItemWriteSerializer
    pagination_class = None
    entity_name = "Item"

    def get_queryset(self):
        return FoodItem.objects.filter(restaurant=self.request.user.restaurant).order_by("display_order")

    def perform_create(self, serializer):
        # category must belong to this restaurant
        category = serializer.validated_data.get("category_id")
        if category and category.restaurant_id != self.request.user.restaurant.id:
            raise PermissionDenied("Category does not belong to your restaurant.")
        restaurant = self.request.user.restaurant
        slug = _unique_item_slug(restaurant, serializer.validated_data.get("name"))
        serializer.save(restaurant=restaurant, slug=slug)

    def perform_update(self, serializer):
        category = serializer.validated_data.get("category_id")
        if category and category.restaurant_id != self.request.user.restaurant.id:
            raise PermissionDenied("Category does not belong to your restaurant.")
        serializer.save()


class VendorRestaurantView(RetrieveUpdateAPIView):
    """GET/PATCH the caller's own restaurant profile. Deliberately not a router-registered
    viewset — there is exactly one object per owner and no pk in the URL. get_object()
    always resolves to request.user.restaurant so this can never leak or edit another
    vendor's restaurant, regardless of request body content (commission/status/slug are
    read-only on the serializer as an additional belt-and-suspenders guard).
    """

    permission_classes = [IsAuthenticated, IsRestaurantOwner]
    authentication_classes = [JWTAuthentication]
    serializer_class = VendorRestaurantSerializer

    def get_object(self):
        return self.request.user.restaurant

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return renderResponse(data=serializer.data, message="Restaurant profile retrieved")

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message="Validation error", status=400)
        serializer.save()
        return renderResponse(data=serializer.data, message="Restaurant profile updated")
