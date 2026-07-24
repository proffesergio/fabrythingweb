from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from core.helpers import renderResponse
from food.permissions import IsRider


class RiderPrivacyView(APIView):
    """Rider's own consent switches: whether their live position is shared to
    the customer-facing track endpoint, and whether nav display is enabled on
    their own dashboard. Both are opt-in — see Rider.is_sharing_location /
    Rider.nav_display_enabled defaults."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsRider]

    def post(self, request):
        rider = request.user.rider
        fields = []
        if "is_sharing_location" in request.data:
            rider.is_sharing_location = bool(request.data["is_sharing_location"])
            fields.append("is_sharing_location")
            if not rider.is_sharing_location:
                rider.current_lat = None
                rider.current_lng = None
                fields += ["current_lat", "current_lng"]
        if "nav_display_enabled" in request.data:
            rider.nav_display_enabled = bool(request.data["nav_display_enabled"])
            fields.append("nav_display_enabled")
        if fields:
            rider.save(update_fields=fields + ["updated_at"])
        return renderResponse(
            data={"is_sharing_location": rider.is_sharing_location,
                  "nav_display_enabled": rider.nav_display_enabled},
            message="Privacy updated")
