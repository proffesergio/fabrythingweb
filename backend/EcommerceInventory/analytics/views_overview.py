"""Module overview APIs for the modular admin shell.

One cheap aggregate endpoint per business (Shop / Food) plus a cross-module
notifications rollup for the topbar bell. Staff-only via IsAnalyticsStaff
(platform staff; other roles get 403 — domain sub-accounts are confined to
their tenant pages, never these platform-wide numbers).

Conventions: `?days=14|30` controls series length (default 14). Money is
returned as floats (BDT). Deltas compare the last 7 days vs the prior 7 and
are None when there is no prior window.
"""
from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import ProductVariant
from food.models import FoodOrder, Restaurant, Rider
from inventory.models import Inventory
from orders.models import Order, OrderItem

from .permissions import IsAnalyticsStaff

VALID_DAYS = (7, 14, 30)


def _days(request, default=14):
    try:
        n = int(request.query_params.get("days", default))
    except (TypeError, ValueError):
        n = default
    return n if n in VALID_DAYS else default


def _day_buckets(days):
    today = timezone.now().date()
    return [today - timedelta(days=i) for i in range(days - 1, -1, -1)]


def _series(qs, date_field, value_field, days):
    """[{day, total, count}] with zero-filled gaps, oldest → newest."""
    since = timezone.now() - timedelta(days=days)
    rows = (
        qs.filter(**{f"{date_field}__gte": since})
        .annotate(day=TruncDate(date_field))
        .values("day")
        .annotate(total=Sum(value_field), n=Count("id"))
        .order_by("day")
    )
    by_day = {r["day"]: r for r in rows}
    out = []
    for d in _day_buckets(days):
        r = by_day.get(d)
        out.append({
            "day": d.isoformat(),
            "total": float(r["total"] or 0) if r else 0.0,
            "count": r["n"] if r else 0,
        })
    return out


def _delta(cur, prev):
    if not prev:
        return None
    return round((cur - prev) / prev * 100, 1)


def _window_sums(qs, date_field, value_field):
    now = timezone.now()
    cur = qs.filter(**{f"{date_field}__gte": now - timedelta(days=7)})
    prev = qs.filter(**{f"{date_field}__gte": now - timedelta(days=14),
                        f"{date_field}__lt": now - timedelta(days=7)})
    cur_sum = float(cur.aggregate(s=Sum(value_field))["s"] or 0)
    prev_sum = float(prev.aggregate(s=Sum(value_field))["s"] or 0)
    return cur_sum, prev_sum, cur.count(), prev.count()


# ── Shop (COD storefront orders) ──────────────────────────────────────────
SHOP_LIVE = [Order.Status.CONFIRMED, Order.Status.OUT_FOR_DELIVERY, Order.Status.DELIVERED]
SHOP_COUNTED = SHOP_LIVE + [Order.Status.PENDING_VERIFICATION]


def shop_numbers(days=14):
    counted = Order.objects.filter(status__in=SHOP_COUNTED)
    live = Order.objects.filter(status__in=SHOP_LIVE)
    rev, prev_rev, n, prev_n = _window_sums(live, "created_at", "total_amount")
    aov = round(rev / n, 2) if n else 0.0
    return {
        "kpis": {
            "revenue_7d": rev,
            "revenue_delta": _delta(rev, prev_rev),
            "orders_7d": n,
            "orders_delta": _delta(n, prev_n),
            "avg_order_value": aov,
            "pending_verification": Order.objects.filter(
                status=Order.Status.PENDING_VERIFICATION).count(),
        },
        "series": _series(live, "created_at", "total_amount", days),
        "top_products": [
            {"name": r["product_name"], "qty": r["qty"],
             "revenue": float(r["revenue"] or 0)}
            for r in OrderItem.objects.filter(order__status__in=SHOP_LIVE)
            .values("product_name")
            .annotate(qty=Sum("quantity"), revenue=Sum("line_total"))
            .order_by("-qty")[:5]
        ],
        "recent_orders": list(
            Order.objects.order_by("-created_at")
            .values("order_number", "status", "total_amount",
                    "contact_name", "created_at")[:6]
        ),
        "alerts": {
            "pending_orders": Order.objects.filter(
                status=Order.Status.PENDING_VERIFICATION).count(),
            "low_stock": ProductVariant.objects.filter(
                is_active=True, stock_quantity__lte=5).count(),
            "out_of_stock": ProductVariant.objects.filter(
                is_active=True, stock_quantity=0).count(),
            "inventory_rows": Inventory.objects.count(),
        },
    }


class ShopOverviewView(APIView):
    permission_classes = [IsAnalyticsStaff]

    def get(self, request):
        return Response({"data": shop_numbers(_days(request))})


# ── Food ──────────────────────────────────────────────────────────────────
FOOD_LIVE = [s for s in FoodOrder.Status if s != FoodOrder.Status.CANCELLED]


def food_numbers(days=14):
    live = FoodOrder.objects.filter(status__in=FOOD_LIVE)
    gmv, prev_gmv, n, prev_n = _window_sums(live, "created_at", "total")
    riders = list(Rider.objects.filter(is_available=True))
    online = sum(1 for r in riders if r.is_online)
    return {
        "kpis": {
            "gmv_7d": gmv,
            "gmv_delta": _delta(gmv, prev_gmv),
            "orders_7d": n,
            "orders_delta": _delta(n, prev_n),
            "active_restaurants": Restaurant.objects.filter(status="ACTIVE").count(),
            "online_riders": online,
        },
        "series": _series(live, "created_at", "total", days),
        "top_restaurants": [
            {"name": r["restaurant__name"], "orders": r["n"],
             "gmv": float(r["gmv"] or 0)}
            for r in live.values("restaurant__name")
            .annotate(n=Count("id"), gmv=Sum("total"))
            .order_by("-n")[:5]
        ],
        "recent_orders": [
            {"code": o["order_code"], "status": o["status"],
             "total": float(o["total"]), "restaurant": o["restaurant__name"],
             "created_at": o["created_at"]}
            for o in FoodOrder.objects.select_related("restaurant")
            .order_by("-created_at")
            .values("order_code", "status", "total",
                    "restaurant__name", "created_at")[:6]
        ],
        "alerts": {
            "unconfirmed_orders": FoodOrder.objects.filter(
                status=FoodOrder.Status.PLACED).count(),
            "pending_partners": Restaurant.objects.filter(status="PENDING").count(),
            "cash_to_collect": float(FoodOrder.objects.filter(
                status=FoodOrder.Status.DELIVERED,
                payment_status="PENDING").aggregate(s=Sum("total"))["s"] or 0),
        },
    }


class FoodOverviewView(APIView):
    permission_classes = [IsAnalyticsStaff]

    def get(self, request):
        return Response({"data": food_numbers(_days(request))})


# ── Notifications rollup (topbar bell) ────────────────────────────────────
class NotificationsView(APIView):
    permission_classes = [IsAnalyticsStaff]

    def get(self, request):
        from nobleseek.models import Article, TrendKeyword
        shop = {
            "pending_orders": Order.objects.filter(
                status=Order.Status.PENDING_VERIFICATION).count(),
            "low_stock": ProductVariant.objects.filter(
                is_active=True, stock_quantity__lte=5).count(),
        }
        food = {
            "unconfirmed_orders": FoodOrder.objects.filter(
                status=FoodOrder.Status.PLACED).count(),
            "pending_partners": Restaurant.objects.filter(status="PENDING").count(),
        }
        news = {
            "review_queue": Article.objects.filter(status=Article.Status.REVIEW).count(),
            "trends_new": TrendKeyword.objects.filter(
                status=TrendKeyword.Status.NEW).count(),
        }
        total = sum(shop.values()) + sum(food.values()) + sum(news.values())
        return Response({"data": {
            "shop": shop, "food": food, "news": news, "total": total,
        }})
