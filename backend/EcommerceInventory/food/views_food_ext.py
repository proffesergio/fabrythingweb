"""Phase A–D feature endpoints: coupons, riders + dispatch, rider dashboard,
notifications, loyalty, and payment reconciliation."""
from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import ListAPIView
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.helpers import renderResponse, CustomPageNumberPagination, CommonListAPIMixin
from food.models import (Restaurant, Coupon, Rider, RiderEarning, FoodOrder, Notification,
                         LoyaltyAccount, PaymentTransaction, DeliveryOffer)
from food.services_dispatch import (accept_offer, decline_offer, assign_rider,
                                    live_offer_for_rider)
from food.permissions import IsRestaurantOwner, IsPlatformAdmin, IsRider
from food.serializers_ext import CouponSerializer, RiderSerializer, NotificationSerializer, PaymentSerializer
from food.serializers_orders import FoodOrderSerializer
from food.serializers_rider import RiderOrderSerializer
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
        wants_login = bool(od.get("username") or od.get("email") or od.get("password"))
        if wants_login and not (od.get("username") and od.get("email") and od.get("password")):
            return renderResponse(data="Owner needs username, email and password.",
                                  message="Validation error", status=400)
        if wants_login and User.objects.filter(
                Q(email=od["email"]) | Q(username=od["username"])).exists():
            return renderResponse(data="A user with that email/username already exists.",
                                  message="Validation error", status=400)

        # Validate the rider BEFORE touching the User table, so a rejected
        # payload can't leave a login account behind with no rider attached.
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message="Validation error", status=400)

        # ATOMIC: the User and the Rider land together or not at all. Without
        # this, a failure on the Rider insert committed the User anyway, and
        # every retry of the same form hit "already exists" forever — the
        # account was orphaned, invisible in the admin panel, and unusable.
        with transaction.atomic():
            owner = None
            if wants_login:
                owner = User.objects.create_user(
                    username=od["username"], email=od["email"], password=od["password"],
                    phone=od.get("phone", ""), role="Rider", country="Bangladesh")
            serializer.save(user=owner)
        return renderResponse(data=serializer.data, message="Rider created", status=201)

    @action(detail=True, methods=["post"], url_path="reset-password")
    def reset_password(self, request, pk=None):
        """Set a new password for this rider's login so an admin can hand over
        working credentials. Riders have no self-serve password reset."""
        rider = self.get_object()
        if not rider.user:
            return renderResponse(data="This rider has no login account.",
                                  message="Validation error", status=400)
        password = (request.data.get("password") or "").strip()
        if len(password) < 8:
            return renderResponse(data="Password must be at least 8 characters.",
                                  message="Validation error", status=400)
        rider.user.set_password(password)
        rider.user.save(update_fields=["password"])
        return renderResponse(data={"username": rider.user.username}, message="Password updated")


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
        # Routes through the dispatch service so any live offer is closed —
        # otherwise a rider could accept an offer for an order an admin just
        # handed to someone else.
        assign_rider(order, rider)
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


class RiderHeartbeatView(APIView):
    """Presence + position ping from the rider dashboard (~every 20s while Online).

    Coordinates are optional: a browser that denies geolocation should still be
    able to keep the rider marked present. Only the current position is stored —
    no location history is kept.

    Storage here is NOT gated on is_sharing_location: the platform always
    tracks online riders' position so dispatch (services_dispatch.py, which
    filters on current_lat/lng being known) keeps working. is_sharing_location
    only gates whether the customer-facing track endpoint exposes this
    position — see food/serializers_orders.py.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsRider]

    def post(self, request):
        rider = request.user.rider
        fields = ["last_seen_at", "updated_at"]
        rider.last_seen_at = timezone.now()
        lat, lng = request.data.get("lat"), request.data.get("lng")
        if lat is not None and lng is not None:
            try:
                rider.current_lat = Decimal(str(lat))
                rider.current_lng = Decimal(str(lng))
            except (InvalidOperation, TypeError):
                return renderResponse(data={"lat": ["Invalid coordinate."]},
                                      message="Validation error", status=400)
            fields += ["current_lat", "current_lng"]
        rider.save(update_fields=fields)
        return renderResponse(data={"last_seen_at": rider.last_seen_at.isoformat()},
                              message="Heartbeat")


class RiderOrdersView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsRider]

    def get(self, request):
        qs = FoodOrder.objects.filter(rider=request.user.rider).exclude(
            status__in=[FoodOrder.Status.DELIVERED, FoodOrder.Status.CANCELLED]
        ).select_related("restaurant").prefetch_related("items")
        return renderResponse(data=RiderOrderSerializer(qs, many=True).data, message="Assigned orders")


class RiderEarningsView(APIView):
    """Today's and lifetime payout, completed deliveries, and cash owed to the
    restaurant from COD orders the rider is still carrying."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsRider]

    def get(self, request):
        rider = request.user.rider
        earnings = list(rider.earnings.select_related("order").order_by("-created_at"))
        today = timezone.localdate()

        lifetime = sum((e.base_pay + e.tip for e in earnings), Decimal("0.00"))
        today_total = sum((e.base_pay + e.tip for e in earnings
                           if timezone.localtime(e.created_at).date() == today), Decimal("0.00"))
        cash = sum((o.total for o in FoodOrder.objects.filter(
            rider=rider, payment_method="COD", payment_status="PENDING"
        ).exclude(status__in=[FoodOrder.Status.DELIVERED, FoodOrder.Status.CANCELLED])),
            Decimal("0.00"))

        history = [{
            "order_code": e.order.order_code if e.order else "",
            "delivered_at": e.created_at.isoformat(),
            "base_pay": str(e.base_pay),
            "tip": str(e.tip),
            "payout": str(e.base_pay + e.tip),
        } for e in earnings[:50]]

        return renderResponse(data={
            "today": str(today_total.quantize(Decimal("0.01"))),
            "lifetime": str(lifetime.quantize(Decimal("0.01"))),
            "cash_to_collect": str(cash.quantize(Decimal("0.01"))),
            "history": history,
        }, message="Rider earnings")


class RiderOfferView(APIView):
    """The offer/accept cycle from the rider's side.

    GET  → the single offer this rider should be answering (or null), with the
           seconds left to answer and enough of the order to decide.
    POST → {"action": "accept"|"decline"}. Accept assigns the order; decline
           cascades it to the next rider. Both route through services_dispatch,
           which locks the order so two riders can never take the same one.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsRider]

    def get(self, request):
        offer = live_offer_for_rider(request.user.rider)
        if not offer:
            return renderResponse(data={"offer": None}, message="No pending offer")
        return renderResponse(data={"offer": self._serialize(offer)}, message="Pending offer")

    def post(self, request):
        offer = (DeliveryOffer.objects
                 .filter(rider=request.user.rider, state=DeliveryOffer.State.OFFERED)
                 .select_related("order").first())
        if not offer:
            return renderResponse(data={}, message="No offer to respond to", status=404)

        action = (request.data.get("action") or "").lower()
        if action == "accept":
            order, ok = accept_offer(offer)
            if not ok:
                # Expired or snatched by an admin between poll and tap.
                return renderResponse(data={"accepted": False},
                                      message="That offer is no longer available", status=409)
            return renderResponse(data={"accepted": True, "order_id": order.id},
                                  message="Delivery accepted")
        if action == "decline":
            decline_offer(offer)
            return renderResponse(data={"declined": True}, message="Offer declined")
        return renderResponse(data={}, message="action must be 'accept' or 'decline'", status=400)

    def _serialize(self, offer):
        o = offer.order
        return {
            "offer_id": offer.id,
            "seconds_left": offer.seconds_left(),
            "order_code": o.order_code,
            "restaurant_name": o.restaurant.name,
            "restaurant_lat": str(o.restaurant.pickup_lat) if o.restaurant.pickup_lat is not None else None,
            "restaurant_lng": str(o.restaurant.pickup_lng) if o.restaurant.pickup_lng is not None else None,
            "delivery_address": o.delivery_address,
            "delivery_lat": str(o.delivery_lat) if o.delivery_lat is not None else None,
            "delivery_lng": str(o.delivery_lng) if o.delivery_lng is not None else None,
            "distance_km": str(o.distance_km) if o.distance_km is not None else None,
            "payment_method": o.payment_method,
            "total": str(o.total),
            # What the rider will be paid for this specific delivery — the
            # distance-priced snapshot, not a flat guess.
            "rider_pay": str((o.rider_base_pay or Decimal("0.00")) + o.tip),
        }


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
            # Pay the distance-priced snapshot taken at checkout, falling back to
            # the flat rate only for orders placed before distance pricing (whose
            # snapshot is 0). This must match services_settlement._base_pay_for,
            # or the rider's dashboard total drifts from the settlement ledger.
            base_pay = order.rider_base_pay if order.rider_base_pay else RIDER_BASE_PAY
            RiderEarning.objects.get_or_create(rider=rider, order=order,
                                               defaults={"base_pay": base_pay, "tip": order.tip})
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
