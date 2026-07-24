from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from core.helpers import renderResponse
from food.models import DeviceToken


class DeviceRegisterView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        expo_token = request.data.get("expo_token")
        app = request.data.get("app")
        platform = request.data.get("platform")
        if not expo_token or app not in DeviceToken.App.values or platform not in DeviceToken.Platform.values:
            return renderResponse(data={}, message="Invalid device payload", status=400)
        DeviceToken.objects.update_or_create(
            expo_token=expo_token,
            defaults={"user": request.user, "app": app, "platform": platform,
                      "enabled": True, "last_seen_at": timezone.now()},
        )
        return renderResponse(data={}, message="Device registered")


class DeviceUnregisterView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        expo_token = request.data.get("expo_token", "")
        DeviceToken.objects.filter(user=request.user, expo_token=expo_token).update(enabled=False)
        return renderResponse(data={}, message="Device unregistered")
