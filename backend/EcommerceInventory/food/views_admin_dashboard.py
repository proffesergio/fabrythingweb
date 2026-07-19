from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.helpers import renderResponse
from food.models import Restaurant, FoodOrder
from food.permissions import IsPlatformAdmin
from food.serializers_orders import FoodOrderSerializer


class AdminFoodDashboardView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        now = timezone.localtime()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = today_start.replace(day=1)

        orders = FoodOrder.objects.all()
        revenue_base = orders.exclude(status=FoodOrder.Status.CANCELLED)

        def revenue(qs):
            return float(qs.aggregate(t=Sum("total"))["t"] or 0)

        # Revenue trend — last 14 days (non-cancelled).
        trend = []
        for i in range(13, -1, -1):
            day = (today_start - timedelta(days=i))
            day_end = day + timedelta(days=1)
            total = revenue(revenue_base.filter(created_at__gte=day, created_at__lt=day_end))
            trend.append({"date": day.strftime("%Y-%m-%d"), "total": total})

        # Top restaurants by non-cancelled revenue.
        top = (revenue_base.values("restaurant__name")
               .annotate(orders=Count("id"), revenue=Sum("total"))
               .order_by("-revenue")[:5])
        top_restaurants = [
            {"name": r["restaurant__name"], "orders": r["orders"], "revenue": float(r["revenue"] or 0)}
            for r in top
        ]

        data = {
            "orders": {
                "today": orders.filter(created_at__gte=today_start).count(),
                "this_month": orders.filter(created_at__gte=month_start).count(),
                "total": orders.count(),
            },
            "revenue": {
                "today": revenue(revenue_base.filter(created_at__gte=today_start)),
                "this_month": revenue(revenue_base.filter(created_at__gte=month_start)),
            },
            "status_distribution": {
                s.value: orders.filter(status=s.value).count() for s in FoodOrder.Status
            },
            "restaurants": {
                "active": Restaurant.objects.filter(status=Restaurant.Status.ACTIVE).count(),
                "pending": Restaurant.objects.filter(status=Restaurant.Status.PENDING).count(),
                "total": Restaurant.objects.count(),
            },
            "revenue_trend": trend,
            "top_restaurants": top_restaurants,
            "recent_orders": FoodOrderSerializer(
                orders.prefetch_related("items").order_by("-created_at")[:10], many=True).data,
        }
        return renderResponse(data=data, message="Food dashboard")
