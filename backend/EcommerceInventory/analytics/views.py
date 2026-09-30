"""Traffic API: public beacon ingest + staff admin endpoints.

Routes (mounted at api/store/analytics/ — inside PUBLIC_API_PREFIXES so the
PermissionMiddleware lets them through; each view enforces its own class):
  POST ingest/            public beacon receiver (AllowAny, throttled)
  GET  admin/overview/    staff: per-provider health + 7-day funnel + totals
  GET  admin/events/      staff: paginated recent TrackedEvent rows
  GET/PATCH admin/providers/[/<key>/]  staff: list / toggle / configure
"""

from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import AnalyticsProvider, TrackedEvent
from .permissions import IsAnalyticsStaff
from .providers import REGISTRY, ensure_default_providers

# Events the frontend is allowed to log. Anything else is dropped — the
# endpoint is public and must not become a junk-data sink for bots.
ALLOWED_EVENTS = {
    "page_view", "view_item", "add_to_cart", "begin_checkout", "purchase",
    "search", "signup", "login",
}

FUNNEL_STEPS = ["page_view", "view_item", "add_to_cart", "begin_checkout", "purchase"]


class IngestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "analytics"

    def post(self, request):
        event = str(request.data.get("event", ""))[:64]
        if event not in ALLOWED_EVENTS:
            # 200, not 400: a mismatched frontend version must never surface
            # an error toast in the shop (APIHandler toasts non-silent errors).
            return Response({"ok": True})
        user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
        params = request.data.get("params")
        TrackedEvent.objects.create(
            event=event,
            path=str(request.data.get("path", ""))[:512],
            session_id=str(request.data.get("session_id", ""))[:64],
            user_id=user.id if user else None,
            params=params if isinstance(params, dict) else {},
        )
        return Response({"ok": True})


class OverviewView(APIView):
    permission_classes = [IsAnalyticsStaff]

    def get(self, request):
        ensure_default_providers()
        rows = {p.key: p for p in AnalyticsProvider.objects.all()}

        providers = []
        for plugin in REGISTRY:
            st = plugin.status(rows.get(plugin.key))
            providers.append({
                "key": st.key, "name": st.name, "is_enabled": st.is_enabled,
                "configured": st.configured, "detail": st.detail,
                "setup_url": st.setup_url, "docs_hint": st.docs_hint,
            })

        since = timezone.now() - timedelta(days=7)
        by_day = (
            TrackedEvent.objects.filter(created_at__gte=since)
            .annotate(day=TruncDate("created_at"))
            .values("day").annotate(count=Count("id")).order_by("day")
        )
        funnel_qs = (
            TrackedEvent.objects.filter(created_at__gte=since, event__in=FUNNEL_STEPS)
            .values("event").annotate(count=Count("id"))
        )
        funnel_counts = {r["event"]: r["count"] for r in funnel_qs}
        funnel = [{step: funnel_counts.get(step, 0)} for step in FUNNEL_STEPS]

        totals = {
            "events_7d": TrackedEvent.objects.filter(created_at__gte=since).count(),
            "sessions_7d": TrackedEvent.objects.filter(created_at__gte=since)
            .values("session_id").distinct().count(),
            "purchases_7d": funnel_counts.get("purchase", 0),
        }
        return Response({
            "data": {"providers": providers, "by_day": list(by_day),
                     "funnel": funnel, "totals": totals}
        })


class EventPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class EventsView(APIView):
    permission_classes = [IsAnalyticsStaff]

    def get(self, request):
        qs = TrackedEvent.objects.all()
        event = request.query_params.get("event")
        if event:
            qs = qs.filter(event=event)
        paginator = EventPagination()
        page = paginator.paginate_queryset(qs, request)
        data = [{
            "id": e.id, "event": e.event, "path": e.path,
            "session_id": e.session_id, "user_id": e.user_id,
            "params": e.params, "created_at": e.created_at,
        } for e in page]
        return paginator.get_paginated_response(data)


class ProvidersView(APIView):
    permission_classes = [IsAnalyticsStaff]

    def get(self, request):
        ensure_default_providers()
        rows = AnalyticsProvider.objects.all()
        return Response({"data": [
            {"key": p.key, "name": p.name, "is_enabled": p.is_enabled,
             "config": p.config, "updated_at": p.updated_at}
            for p in rows
        ]})

    def patch(self, request, key):
        try:
            provider = AnalyticsProvider.objects.get(key=key)
        except AnalyticsProvider.DoesNotExist:
            return Response({"message": "Unknown provider"}, status=404)
        if "is_enabled" in request.data:
            provider.is_enabled = bool(request.data["is_enabled"])
        if isinstance(request.data.get("config"), dict):
            merged = dict(provider.config or {})
            merged.update(request.data["config"])
            provider.config = merged
        provider.save()
        return Response({"data": {
            "key": provider.key, "name": provider.name,
            "is_enabled": provider.is_enabled, "config": provider.config,
        }})
