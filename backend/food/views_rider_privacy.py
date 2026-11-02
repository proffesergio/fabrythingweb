from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from core.helpers import renderResponse
from food.permissions import IsRider

_FALSY_STRINGS = {"false", "0", "", "no"}


def _coerce_bool(value):
    """bool("false") is True in Python, so a stringy "false" from a client
    would silently flip a flag on. Real booleans pass through unchanged;
    strings are matched case-insensitively against a falsy set; anything
    else (including other truthy strings/numbers) is treated as truthy."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in _FALSY_STRINGS
    return bool(value)


class RiderPrivacyView(APIView):
    """Rider's own consent switches: whether their live position is shared to
    the customer-facing track endpoint, and whether nav display is enabled on
    their own dashboard. is_sharing_location defaults on (customers see the
    rider during an active delivery); nav_display_enabled also defaults on.

    Note: is_sharing_location gates only the customer-facing view — it never
    clears current_lat/current_lng. The platform always tracks online riders'
    position (via the heartbeat) regardless of this flag, because dispatch
    needs a known position to assign orders."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsRider]

    def post(self, request):
        rider = request.user.rider
        fields = []
        if "is_sharing_location" in request.data:
            rider.is_sharing_location = _coerce_bool(request.data["is_sharing_location"])
            fields.append("is_sharing_location")
        if "nav_display_enabled" in request.data:
            rider.nav_display_enabled = _coerce_bool(request.data["nav_display_enabled"])
            fields.append("nav_display_enabled")
        if fields:
            rider.save(update_fields=fields + ["updated_at"])
        return renderResponse(
            data={"is_sharing_location": rider.is_sharing_location,
                  "nav_display_enabled": rider.nav_display_enabled},
            message="Privacy updated")
