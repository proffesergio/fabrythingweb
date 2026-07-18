from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.helpers import renderResponse
from food.models import Restaurant, DeliveryZone
from food.permissions import IsPlatformAdmin
from food.serializers_admin import RestaurantAdminSerializer, DeliveryZoneAdminSerializer
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

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._set_status(pk, Restaurant.Status.ACTIVE)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        return self._set_status(pk, Restaurant.Status.SUSPENDED)


class AdminZoneViewSet(EnvelopeModelViewSetMixin, ModelViewSet):
    # SECURITY: same rationale as AdminRestaurantViewSet above — IsPlatformAdmin
    # is required, not optional, because PermissionMiddleware bypasses /api/food/.
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    serializer_class = DeliveryZoneAdminSerializer
    queryset = DeliveryZone.objects.all().order_by("name")
    entity_name = "Zone"
