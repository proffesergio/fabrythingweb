from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.helpers import renderResponse, CustomPageNumberPagination, CommonListAPIMixin
from food.models import FoodOrder
from food.services import place_food_cod_order
from food.serializers_orders import FoodOrderSerializer
from food.permissions import IsRestaurantOwner, IsPlatformAdmin


class FoodOrderView(APIView):
    """POST = place a COD order (guest or auth). GET = auth customer's history."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        d = request.data
        try:
            order = place_food_cod_order(
                customer=request.user,
                restaurant_slug=d.get("restaurant_slug"),
                items=d.get("items") or [],
                contact_name=d.get("contact_name", ""),
                contact_phone=d.get("contact_phone", ""),
                delivery_address=d.get("delivery_address", ""),
                zone_id=d.get("zone_id"),
                lat=d.get("lat"), lng=d.get("lng"),
                tip=d.get("tip", "0.00"),
                notes=d.get("notes", ""),
            )
        except ValidationError as exc:
            detail = exc.detail
            msgs = detail if isinstance(detail, list) else [str(detail)]
            return renderResponse(data=[str(m) for m in msgs],
                                  message="Could not place order", status=400)
        return renderResponse(data=FoodOrderSerializer(order).data,
                              message="Order placed", status=201)

    def get(self, request):
        if not request.user.is_authenticated:
            return renderResponse(data=[], message="Login required", status=401)
        qs = FoodOrder.objects.filter(customer=request.user).prefetch_related("items")
        return renderResponse(data=FoodOrderSerializer(qs, many=True).data,
                              message="Order history")


class FoodOrderTrackView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    def get(self, request, order_code):
        order = FoodOrder.objects.filter(order_code=order_code).prefetch_related("items").first()
        if not order:
            return renderResponse(data={}, message="Order not found", status=404)
        if request.user.is_authenticated and order.customer_id == request.user.id:
            pass
        elif request.GET.get("phone") and request.GET.get("phone") == order.guest_phone:
            pass
        else:
            return renderResponse(data={}, message="Order not found", status=404)
        return renderResponse(data=FoodOrderSerializer(order).data, message="Order")


class VendorOrderListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsRestaurantOwner]

    def get(self, request):
        qs = FoodOrder.objects.filter(restaurant=request.user.restaurant).prefetch_related("items")
        status_f = request.GET.get("status")
        if status_f:
            qs = qs.filter(status=status_f)
        return renderResponse(data=FoodOrderSerializer(qs, many=True).data, message="Vendor orders")


class VendorOrderStatusView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsRestaurantOwner]

    def patch(self, request, pk):
        order = FoodOrder.objects.filter(pk=pk, restaurant=request.user.restaurant).first()
        if not order:
            return renderResponse(data={}, message="Order not found", status=404)
        try:
            order.transition_to(request.data.get("status"), changed_by=request.user,
                                reason=request.data.get("reason", ""))
        except ValidationError as exc:
            return renderResponse(data=str(exc.detail), message="Invalid transition", status=400)
        return renderResponse(data={"id": order.id, "status": order.status}, message="Status updated")


class AdminFoodOrderListView(ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    serializer_class = FoodOrderSerializer
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        qs = FoodOrder.objects.all().prefetch_related("items").order_by("-created_at")
        status_f = self.request.GET.get("status")
        if status_f:
            qs = qs.filter(status=status_f)
        return qs

    @CommonListAPIMixin.common_list_decorator(FoodOrderSerializer)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class AdminFoodOrderDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request, pk):
        order = FoodOrder.objects.filter(pk=pk).prefetch_related("items").first()
        if not order:
            return renderResponse(data={}, message="Order not found", status=404)
        data = FoodOrderSerializer(order).data
        data["allowed_transitions"] = [s.value for s in FoodOrder.ALLOWED_TRANSITIONS.get(order.status, [])]
        return renderResponse(data=data, message="Order detail")


class AdminFoodOrderStatusView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def patch(self, request, pk):
        order = FoodOrder.objects.filter(pk=pk).first()
        if not order:
            return renderResponse(data={}, message="Order not found", status=404)
        try:
            order.transition_to(request.data.get("status"), changed_by=request.user,
                                reason=request.data.get("reason", ""))
        except ValidationError as exc:
            return renderResponse(data=str(exc.detail), message="Invalid transition", status=400)
        return renderResponse(data={"id": order.id, "status": order.status}, message="Status updated")
