from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.helpers import renderResponse
from food.models import Restaurant, DeliveryZone, RestaurantZone
from food.permissions import IsPlatformAdmin
from food.serializers_admin import RestaurantAdminSerializer, DeliveryZoneAdminSerializer
from food.services_admin import create_restaurant_with_owner, replace_hours
from food.views_vendor import EnvelopeModelViewSetMixin


class AdminRestaurantViewSet(EnvelopeModelViewSetMixin, ModelViewSet):
    # SECURITY: /api/food/ is in core.middleware.PUBLIC_API_PREFIXES, so
    # PermissionMiddleware never gates this route. IsPlatformAdmin (not just
    # IsAuthenticated) is the only thing stopping a Customer/Rider/Restaurant
    # vendor from approving/suspending restaurants. Do not drop it.
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    serializer_class = RestaurantAdminSerializer
    queryset = Restaurant.objects.all().order_by("-created_at")
    entity_name = "Restaurant"

    def _set_status(self, pk, status):
        r = self.get_object()
        r.status = status
        r.save(update_fields=["status", "updated_at"])
        return renderResponse(data=RestaurantAdminSerializer(r).data, message=f"Restaurant {status.lower()}")

    def create(self, request, *args, **kwargs):
        # Full onboarding: restaurant + optional owner login + zones + hours.
        try:
            restaurant = create_restaurant_with_owner(request.data)
        except ValidationError as exc:
            detail = exc.detail
            msg = detail[0] if isinstance(detail, list) else str(detail)
            return renderResponse(data=str(msg), message="Validation error", status=400)
        return renderResponse(data=RestaurantAdminSerializer(restaurant).data,
                              message="Restaurant created", status=201)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._set_status(pk, Restaurant.Status.ACTIVE)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        return self._set_status(pk, Restaurant.Status.SUSPENDED)

    @action(detail=True, methods=["post", "delete"])
    def zones(self, request, pk=None):
        r = self.get_object()
        zone = DeliveryZone.objects.filter(id=request.data.get("zone_id")).first()
        if not zone:
            return renderResponse(data={}, message="Zone not found", status=404)
        if request.method == "DELETE":
            RestaurantZone.objects.filter(restaurant=r, zone=zone).delete()
            return renderResponse(data={}, message="Zone removed")
        RestaurantZone.objects.update_or_create(
            restaurant=r, zone=zone, defaults={"delivery_fee": request.data.get("delivery_fee")})
        return renderResponse(data={}, message="Zone assigned")

    @action(detail=True, methods=["put"])
    def hours(self, request, pk=None):
        r = self.get_object()
        replace_hours(r, request.data.get("hours", []) or [])
        return renderResponse(data={}, message="Hours updated")


class AdminZoneViewSet(EnvelopeModelViewSetMixin, ModelViewSet):
    # SECURITY: same rationale as AdminRestaurantViewSet above — IsPlatformAdmin
    # is required, not optional, because PermissionMiddleware bypasses /api/food/.
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    serializer_class = DeliveryZoneAdminSerializer
    queryset = DeliveryZone.objects.all().order_by("name")
    entity_name = "Zone"
