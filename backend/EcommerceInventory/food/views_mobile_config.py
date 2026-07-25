from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from core.helpers import renderResponse

MOBILE_CONFIG = {
    "min_supported_version": {"customer": "1.0.0", "rider": "1.0.0", "restaurant": "1.0.0"},
    "feature_flags": {"whatsapp_offers": False, "online_payment": False},
    "support": {
        "facebook_url": "https://www.facebook.com/fabrything",
        "messenger_url": "https://m.me/fabrything",
    },
    "tile_url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
}


class MobileConfigView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return renderResponse(data=MOBILE_CONFIG, message="Mobile config")
