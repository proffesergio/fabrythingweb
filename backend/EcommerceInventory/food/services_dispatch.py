"""Choosing which rider gets an order.

Riders use the web dashboard, not a native app, so "who is online right now" is
derived from the heartbeat that page sends (see Rider.PRESENCE_WINDOW_MINUTES
and views_food_ext.RiderHeartbeatView) rather than from a standing flag alone.
"""
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from food.geo import haversine_km
from food.models import FoodOrder, Rider
from food.services import notify

ACTIVE_STATUSES = [FoodOrder.Status.CONFIRMED, FoodOrder.Status.PREPARING,
                   FoodOrder.Status.OUT_FOR_DELIVERY]


def dispatchable_riders():
    """Riders who are available, recently seen, and have a known position."""
    cutoff = timezone.now() - timedelta(minutes=Rider.PRESENCE_WINDOW_MINUTES)
    return Rider.objects.filter(
        is_available=True,
        last_seen_at__gte=cutoff,
        current_lat__isnull=False,
        current_lng__isnull=False,
    )


def pick_rider_for(order):
    """Nearest dispatchable rider to the pickup point, else the least loaded.

    Riders have no zone association in the current model, so there is no zone
    filter to fall back on — load, then staleness, is the tiebreak instead.
    """
    riders = list(dispatchable_riders())
    if not riders:
        return None

    restaurant = order.restaurant
    if restaurant.pickup_lat is not None and restaurant.pickup_lng is not None:
        return min(riders, key=lambda r: haversine_km(
            restaurant.pickup_lat, restaurant.pickup_lng, r.current_lat, r.current_lng))

    ranked = dispatchable_riders().annotate(
        active_orders=Count("orders", filter=Q(orders__status__in=ACTIVE_STATUSES))
    ).order_by("active_orders", "last_seen_at")
    return ranked.first()


def maybe_auto_assign_rider(order):
    """Assign a rider to a freshly confirmed order. Returns the rider or None.

    Idempotent: an order that already has a rider is never reassigned, so an
    admin's manual choice always wins.
    """
    if order.rider_id or order.status != FoodOrder.Status.CONFIRMED:
        return None
    rider = pick_rider_for(order)
    if rider is None:
        return None

    order.rider = rider
    order.save(update_fields=["rider", "updated_at"])
    notify(rider.user, f"New delivery {order.order_code}",
           f"Pick up from {order.restaurant.name} 🛵", order.order_code)
    notify(order.customer, f"Order {order.order_code}",
           f"{rider.name} will deliver your order 🛵", order.order_code)
    return rider
