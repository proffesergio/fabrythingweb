"""Admin settlement (Payments tab) and bilingual zone/village management."""
from decimal import Decimal

from django.db.models import Sum, Q
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.helpers import renderResponse, CustomPageNumberPagination, CommonListAPIMixin
from food.models import OrderSettlement, Village, DeliveryZone
from food.permissions import IsPlatformAdmin
from food.serializers_settlement import (
    SettlementSerializer, VillageAdminSerializer, ZoneWithVillagesSerializer,
)
from food.services_settlement import settle_leg
from food.views_vendor import EnvelopeModelViewSetMixin


class AdminSettlementListView(ListAPIView):
    """The Payments tab. Every delivered order with its money split and the
    state of each of the four settlement legs."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    serializer_class = SettlementSerializer
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        qs = (OrderSettlement.objects
              .select_related("order", "order__restaurant", "rider")
              .order_by("-created_at"))
        p = self.request.GET
        if p.get("rider"):
            qs = qs.filter(rider_id=p["rider"])
        if p.get("restaurant"):
            qs = qs.filter(order__restaurant_id=p["restaurant"])
        if p.get("method"):
            qs = qs.filter(order__payment_method=p["method"])
        # Filter by the state of a single leg, e.g. ?leg=rider_payout&status=PENDING
        leg, status_f = p.get("leg"), p.get("status")
        if leg in OrderSettlement.LEGS and status_f:
            qs = qs.filter(**{OrderSettlement.LEGS[leg][0]: status_f})
        if p.get("unsettled") == "true":
            pending = Q()
            for status_field, _ in OrderSettlement.LEGS.values():
                pending |= Q(**{status_field: OrderSettlement.Settle.PENDING})
            qs = qs.filter(pending)
        if p.get("from"):
            qs = qs.filter(created_at__date__gte=p["from"])
        if p.get("to"):
            qs = qs.filter(created_at__date__lte=p["to"])
        return qs

    @CommonListAPIMixin.common_list_decorator(SettlementSerializer)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class AdminSettlementSummaryView(APIView):
    """Totals for the Payments tab header — what's owed and what's been paid."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        qs = OrderSettlement.objects.all()
        if request.GET.get("from"):
            qs = qs.filter(created_at__date__gte=request.GET["from"])
        if request.GET.get("to"):
            qs = qs.filter(created_at__date__lte=request.GET["to"])

        def total(field, **filters):
            return str((qs.filter(**filters).aggregate(t=Sum(field))["t"] or Decimal("0.00")))

        P = OrderSettlement.Settle.PENDING
        return renderResponse(data={
            "orders": qs.count(),
            "gross": total("food_net"),
            "platform_revenue": total("platform_revenue"),
            "commission": total("commission_amount"),
            "outstanding": {
                # Money we are still waiting to receive.
                "customer_payment": total("order__total", customer_payment_status=P),
                "rider_cash": total("order__total", rider_cash_status=P),
                # Money we still owe out.
                "rider_payout": total("rider_payout", rider_payout_status=P),
                "restaurant_payout": total("restaurant_payout", restaurant_payout_status=P),
            },
            "counts": {
                leg: qs.filter(**{status_field: P}).count()
                for leg, (status_field, _) in OrderSettlement.LEGS.items()
            },
        }, message="Settlement summary")


class AdminSettlementLegView(APIView):
    """Mark one leg of one settlement paid (or undo it).

    POST {"leg": "rider_payout", "settled": true}
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def post(self, request, pk):
        settlement = OrderSettlement.objects.filter(pk=pk).first()
        if not settlement:
            return renderResponse(data={}, message="Settlement not found", status=404)
        leg = request.data.get("leg")
        if leg not in OrderSettlement.LEGS:
            return renderResponse(data=f"Unknown leg '{leg}'.",
                                  message="Validation error", status=400)
        settled = request.data.get("settled", True)
        settle_leg(settlement, leg, settled=bool(settled), user=request.user)
        settlement.refresh_from_db()
        return renderResponse(data=SettlementSerializer(settlement).data,
                              message="Settlement updated")


class AdminSettlementBulkLegView(APIView):
    """Settle the same leg across many settlements at once — e.g. paying a
    rider's whole week in one click.

    POST {"ids": [1,2,3], "leg": "rider_payout", "settled": true}
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def post(self, request):
        leg = request.data.get("leg")
        if leg not in OrderSettlement.LEGS:
            return renderResponse(data=f"Unknown leg '{leg}'.",
                                  message="Validation error", status=400)
        ids = request.data.get("ids") or []
        if not isinstance(ids, list) or not ids:
            return renderResponse(data="Provide a non-empty list of settlement ids.",
                                  message="Validation error", status=400)
        settled = bool(request.data.get("settled", True))
        updated = 0
        for settlement in OrderSettlement.objects.filter(id__in=ids).select_related("order"):
            settle_leg(settlement, leg, settled=settled, user=request.user)
            updated += 1
        return renderResponse(data={"updated": updated}, message=f"{updated} settlement(s) updated")


# ── Bilingual delivery geography ─────────────────────────────────────────────
class AdminZoneTreeView(APIView):
    """Every union with its villages nested, both languages — the shape the
    admin zone editor and the customer address picker both want."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        zones = DeliveryZone.objects.prefetch_related("villages").order_by("name")
        return renderResponse(data=ZoneWithVillagesSerializer(zones, many=True).data,
                              message="Zones retrieved")


class AdminVillageViewSet(EnvelopeModelViewSetMixin, ModelViewSet):
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    serializer_class = VillageAdminSerializer
    pagination_class = None
    entity_name = "Village"

    def get_queryset(self):
        qs = Village.objects.select_related("zone").order_by("zone__name", "name")
        if self.request.GET.get("zone"):
            qs = qs.filter(zone_id=self.request.GET["zone"])
        return qs
