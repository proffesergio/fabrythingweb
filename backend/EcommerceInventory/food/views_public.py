from django.db.models import Prefetch
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from core.helpers import renderResponse, CustomPageNumberPagination, CommonListAPIMixin
from food.models import Restaurant, FoodCategory, FoodItem, FoodItemOptionGroup, DeliveryZone
from food.serializers import RestaurantListSerializer, RestaurantDetailSerializer, DeliveryZoneSerializer


def _lang(request):
    return "bn" if request.GET.get("lang") == "bn" else "en"


class PublicRestaurantListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = RestaurantListSerializer
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        qs = Restaurant.objects.filter(status=Restaurant.Status.ACTIVE)
        zone = self.request.GET.get("zone")
        if zone:
            qs = qs.filter(zones__id=zone).distinct()
        search = self.request.GET.get("search")
        if search:
            qs = qs.filter(name__icontains=search)
        cuisine = self.request.GET.get("cuisine")
        if cuisine:
            qs = qs.filter(cuisine_type__icontains=cuisine)
        return qs.order_by("name")

    def get_serializer_context(self):
        return {"lang": _lang(self.request)}

    # Wrap the paginated list in the project's standard renderResponse envelope
    # ({"data": {"data": [...], "totalPages": ..., ...}, "message": ...}) —
    # the same convention every other public list endpoint in this codebase uses
    # (see storefront.views.CustomerOrderListView / AdminOrderListView).
    @CommonListAPIMixin.common_list_decorator(RestaurantListSerializer)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


def _detail_prefetch():
    opt_groups = Prefetch(
        "option_groups",
        queryset=FoodItemOptionGroup.objects.prefetch_related("options"),
    )
    items = Prefetch("items", queryset=FoodItem.objects.prefetch_related(opt_groups))
    cats = Prefetch("categories", queryset=FoodCategory.objects.prefetch_related(items))
    return cats


class PublicRestaurantDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        restaurant = (
            Restaurant.objects.filter(status=Restaurant.Status.ACTIVE, slug=slug)
            .prefetch_related(_detail_prefetch())
            .first()
        )
        if not restaurant:
            return renderResponse(data={}, message="Restaurant not found", status=404)
        data = RestaurantDetailSerializer(restaurant, context={"lang": _lang(request)}).data
        return renderResponse(data=data, message="Restaurant detail")


class PublicZoneListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = DeliveryZoneSerializer
    pagination_class = None

    def get_queryset(self):
        return DeliveryZone.objects.filter(is_active=True).order_by("name")
