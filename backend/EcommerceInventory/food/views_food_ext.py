"""Phase A–D feature endpoints: coupons, riders + dispatch, rider dashboard,
notifications, loyalty, and payment reconciliation."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.helpers import renderResponse, CustomPageNumberPagination, CommonListAPIMixin
from food.models import (Restaurant, Coupon, Rider, RiderEarning, FoodOrder, Notification,
                         LoyaltyAccount, PaymentTransaction)
from food.permissions import IsRestaurantOwner, IsPlatformAdmin, IsRider
from food.serializers_ext import CouponSerializer, RiderSerializer, NotificationSerializer, PaymentSerializer
from food.serializers_orders import FoodOrderSerializer
from food.services import notify
from food.views_vendor import EnvelopeModelViewSetMixin

User = get_user_model()
RIDER_BASE_PAY = Decimal("40.00")


# ── Coupons ──────────────────────────────────────────────────────────────────
class VendorCouponViewSet(EnvelopeModelViewSetMixin, ModelViewSet):
    permission_classes = [IsAuthenticated, IsRestaurantOwner]
    serializer_class = CouponSerializer
    pagination_class = None
    entity_name = "Coupon"

    def get_queryset(self):
        return Coupon.objects.filter(restaurant=self.request.user.restaurant).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(restaurant=self.request.user.restaurant)

    def perform_update(self, serializer):
        serializer.save(restaurant=self.request.user.restaurant)


class AdminCouponViewSet(EnvelopeModelViewSetMixin, ModelViewSet):
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    serializer_class = CouponSerializer
    pagination_class = None
    entity_name = "Coupon"
    queryset = Coupon.objects.all().order_by("-created_at")


class CouponValidateView(APIView):
    """Checkout preview: is this code valid for this cart? Returns the discount."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        code = (request.data.get("code") or "").strip()
        restaurant = Restaurant.objects.filter(slug=request.data.get("restaurant_slug"),
                                               status=Restaurant.Status.ACTIVE).first()
        if not restaurant:
            return renderResponse(data={}, message="Restaurant not found", status=404)
        subtotal = Decimal(str(request.data.get("subtotal") or "0"))
        coupon = Coupon.objects.filter(code__iexact=code).first()
        if not coupon:
            return renderResponse(data={"valid": False, "message": "Invalid coupon code."}, message="Invalid")
        err = coupon.error_for(restaurant, subtotal, timezone.localtime())
        if err:
            return renderResponse(data={"valid": False, "message": err}, message="Invalid")
        return renderResponse(data={"valid": True, "code": coupon.code,
                                    "discount": str(coupon.discount_for(subtotal))}, message="Valid")


# ── Riders (admin) + dispatch ────────────────────────────────────────────────
class AdminRiderViewSet(EnvelopeModelViewSetMixin, ModelViewSet):
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    serializer_class = RiderSerializer
    pagination_class = None
    entity_name = "Rider"
    queryset = Rider.objects.all().order_by("-created_at")

    def create(self, request, *args, **kwargs):
        od = request.data.get("owner") or {}
        owner = None
        if od.get("username") or od.get("email") or od.get("password"):
            if not (od.get("username") and od.get("email") and od.get("password")):
                return renderResponse(data="Owner needs username, email and password.", message="Validation error", status=400)
            if User.objects.filter(email=od["email"]).exists() or User.objects.filter(username=od["username"]).exists():
                return renderResponse(data="A user with that email/username already exists.", message="Validation error", status=400)
            owner = User.objects.create_user(username=od["username"], email=od["email"], password=od["password"],
                                             phone=od.get("phone", ""), role="Rider", country="Bangladesh")
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message="Validation error", status=400)
        serializer.save(user=owner)
        return renderResponse(data=serializer.data, message="Rider created", status=201)


class AdminAssignRiderView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def post(self, request, pk):
        order = FoodOrder.objects.filter(pk=pk).first()
        if not order:
            return renderResponse(data={}, message="Order not found", status=404)
        rider = Rider.objects.filter(pk=request.data.get("rider_id")).first()
        if not rider:
            return renderResponse(data={}, message="Rider not found", status=400)
        order.rider = rider
        order.save(update_fields=["rider", "updated_at"])
        notify(order.customer, f"Order {order.order_code}", f"{rider.name} will deliver your order 🛵", order.order_code)
        return renderResponse(data={"rider_id": rider.id, "rider_name": rider.name}, message="Rider assigned")


# ── Rider dashboard (role: Rider) ────────────────────────────────────────────
class RiderMeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsRider]

    def get(self, request):
        rider = request.user.rider
        earnings = rider.earnings.all()
        total = sum((e.base_pay + e.tip for e in earnings), Decimal("0.00"))
        return renderResponse(data={**RiderSerializer(rider).data, "total_earnings": str(total)},
                              message="Rider profile")


class RiderAvailabilityView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsRider]

    def post(self, request):
        rider = request.user.rider
        rider.is_available = bool(request.data.get("is_available"))
        rider.save(update_fields=["is_available", "updated_at"])
        return renderResponse(data={"is_available": rider.is_available}, message="Availability updated")


class RiderOrdersView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsRider]

    def get(self, request):
        qs = FoodOrder.objects.filter(rider=request.user.rider).exclude(
            status__in=[FoodOrder.Status.DELIVERED, FoodOrder.Status.CANCELLED]).prefetch_related("items")
        return renderResponse(data=FoodOrderSerializer(qs, many=True).data, message="Assigned orders")


class RiderOrderStatusView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsRider]

    def patch(self, request, pk):
        order = FoodOrder.objects.filter(pk=pk, rider=request.user.rider).first()
        if not order:
            return renderResponse(data={}, message="Order not found", status=404)
        new_status = request.data.get("status")
        from rest_framework.exceptions import ValidationError
        try:
            order.transition_to(new_status, changed_by=request.user)
        except ValidationError as exc:
            return renderResponse(data=str(exc.detail), message="Invalid transition", status=400)
        if order.status == FoodOrder.Status.DELIVERED:
            rider = request.user.rider
            RiderEarning.objects.get_or_create(rider=rider, order=order,
                                               defaults={"base_pay": RIDER_BASE_PAY, "tip": order.tip})
            rider.total_deliveries += 1
            rider.save(update_fields=["total_deliveries", "updated_at"])
            notify(order.customer, f"Order {order.order_code}", "Delivered — enjoy your meal! 🍽️", order.order_code)
        return renderResponse(data={"id": order.id, "status": order.status}, message="Status updated")


# ── Notifications ────────────────────────────────────────────────────────────
class NotificationView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Notification.objects.filter(user=request.user)[:30]
        unread = Notification.objects.filter(user=request.user, is_read=False).count()
        return renderResponse(data={"unread": unread, "items": NotificationSerializer(qs, many=True).data},
                              message="Notifications")

    def post(self, request):  # mark all read
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return renderResponse(data={}, message="Marked read")


# ── Loyalty ──────────────────────────────────────────────────────────────────
class LoyaltyView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        acct, _ = LoyaltyAccount.objects.get_or_create(user=request.user)
        entries = acct.entries.all()[:20]
        return renderResponse(data={
            "points": acct.points,
            "entries": [{"delta": e.delta, "reason": e.reason, "order_code": e.order_code,
                         "created_at": e.created_at} for e in entries],
        }, message="Loyalty")


# ── Payments (admin reconciliation) ──────────────────────────────────────────
class AdminPaymentListView(ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    serializer_class = PaymentSerializer
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        qs = PaymentTransaction.objects.select_related("order").order_by("-created_at")
        method = self.request.GET.get("method")
        status_f = self.request.GET.get("status")
        if method:
            qs = qs.filter(method=method)
        if status_f:
            qs = qs.filter(status=status_f)
        return qs

    @CommonListAPIMixin.common_list_decorator(PaymentSerializer)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
