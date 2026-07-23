"""Choosing which rider gets an order, and running the offer/accept cycle.

Riders use the web dashboard, not a native app, so "who is online right now" is
derived from the heartbeat that page sends (see Rider.PRESENCE_WINDOW_MINUTES
and views_food_ext.RiderHeartbeatView) rather than from a standing flag alone.

A CONFIRMED order is not assigned to a rider — it is **offered** to one, who
accepts or declines within a deadline. A declined or expired offer cascades to
the next-nearest rider; when the pool is exhausted the order sits unassigned and
the admin queue takes over. `offer_order` is the engine; `sweep_offers` is what
keeps it moving without a job runner (see the note there).
"""
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from food.geo import haversine_km
from food.models import DeliveryOffer, FoodOrder, Rider
from food.services import notify
from food.services_cash import riders_over_ceiling

ACTIVE_STATUSES = [FoodOrder.Status.CONFIRMED, FoodOrder.Status.PREPARING,
                   FoodOrder.Status.OUT_FOR_DELIVERY]

# An order can be handed to a rider only while the kitchen has it and no rider is
# yet carrying it. Once OUT_FOR_DELIVERY it necessarily already has one.
OFFERABLE_STATUSES = [FoodOrder.Status.CONFIRMED, FoodOrder.Status.PREPARING]

# How long a rider has to answer before the offer cascades to the next rider.
OFFER_TTL_SECONDS = 60


def is_cash_order(order):
    """Only a COD order puts the platform's money in a rider's pocket."""
    return (order.payment_method or "COD").upper() == "COD"


def dispatchable_riders():
    """Riders who are available, recently seen, and have a known position."""
    cutoff = timezone.now() - timedelta(minutes=Rider.PRESENCE_WINDOW_MINUTES)
    return Rider.objects.filter(
        is_available=True,
        last_seen_at__gte=cutoff,
        current_lat__isnull=False,
        current_lng__isnull=False,
    )


def _eligible_riders(order, *, exclude_ids=()):
    """Dispatchable riders who may take THIS order.

    Excludes riders already offered it (one shot each, so a decline cascades to
    someone new instead of looping) and — for cash orders only — riders holding
    too much undeposited COD cash (services_cash.over_ceiling). A prepaid order
    ignores the cash filter, so a rider over the limit still gets prepaid work.
    """
    riders = list(dispatchable_riders().exclude(id__in=exclude_ids))
    if is_cash_order(order):
        blocked = riders_over_ceiling()
        riders = [r for r in riders if r.id not in blocked]
    return riders


def pick_rider_for(order, *, exclude_ids=()):
    """Nearest eligible rider to the pickup point, else the least loaded.

    Riders have no zone association in the current model, so there is no zone
    filter to fall back on — load, then staleness, is the tiebreak instead.
    """
    riders = _eligible_riders(order, exclude_ids=exclude_ids)
    if not riders:
        return None

    restaurant = order.restaurant
    if restaurant.pickup_lat is not None and restaurant.pickup_lng is not None:
        return min(riders, key=lambda r: haversine_km(
            restaurant.pickup_lat, restaurant.pickup_lng, r.current_lat, r.current_lng))

    # Rank the *already filtered* list, not a fresh queryset — re-querying here
    # would quietly reintroduce a rider the filter above excluded.
    ids = [r.id for r in riders]
    ranked = (Rider.objects.filter(id__in=ids).annotate(
        active_orders=Count("orders", filter=Q(orders__status__in=ACTIVE_STATUSES))
    ).order_by("active_orders", "last_seen_at"))
    return ranked.first()


def _riders_already_tried(order):
    """Everyone who has already been offered this order, in any state — so the
    cascade always moves to someone new rather than re-pestering a decliner."""
    return set(order.delivery_offers.values_list("rider_id", flat=True))


@transaction.atomic
def offer_order(order):
    """Ensure the order has a live offer out (or is assigned, or is out of riders).

    The one entry point for putting an order in front of a rider. Idempotent and
    safe to call repeatedly:
      - already has a rider (admin assigned, or an offer was accepted) → no-op
      - already has a live OFFERED offer → returns it, does not double-offer
      - otherwise offers the next-nearest untried rider
      - no rider left → returns None; the order waits in the admin queue

    Returns the live DeliveryOffer, or None.
    """
    order = FoodOrder.objects.select_for_update().get(pk=order.pk)
    if order.rider_id or order.status not in OFFERABLE_STATUSES:
        return None

    now = timezone.now()
    # Expire our own stale offers first, so "is there a live one?" is honest.
    order.delivery_offers.filter(state=DeliveryOffer.State.OFFERED,
                                 expires_at__lte=now).update(
        state=DeliveryOffer.State.EXPIRED, responded_at=now)

    live = order.delivery_offers.filter(state=DeliveryOffer.State.OFFERED).first()
    if live:
        return live

    rider = pick_rider_for(order, exclude_ids=_riders_already_tried(order))
    if rider is None:
        return None

    offer = DeliveryOffer.objects.create(
        order=order, rider=rider, offered_at=now,
        expires_at=now + timedelta(seconds=OFFER_TTL_SECONDS))
    notify(rider.user, f"New delivery offer {order.order_code}",
           f"Pick up from {order.restaurant.name} 🛵 — accept within {OFFER_TTL_SECONDS}s",
           order.order_code)
    return offer


# Kept as the name the order flow calls on CONFIRMED. It now *offers* rather than
# assigns — the rider still has to accept — but the call site is unchanged.
maybe_auto_assign_rider = offer_order


@transaction.atomic
def accept_offer(offer):
    """A rider takes the delivery. Assigns the order and closes the offer.

    Guards against the race where the offer expired (or the order was assigned by
    an admin) between the rider seeing it and tapping Accept: the order is locked
    and re-checked, so a rider can never grab an order that already has one.
    """
    order = FoodOrder.objects.select_for_update().get(pk=offer.order_id)
    offer.refresh_from_db()

    if order.rider_id:
        # Someone else already has it (admin override, typically).
        if order.rider_id != offer.rider_id and offer.state == DeliveryOffer.State.OFFERED:
            offer.state = DeliveryOffer.State.EXPIRED
            offer.responded_at = timezone.now()
            offer.save(update_fields=["state", "responded_at", "updated_at"])
        return order, False
    if not offer.is_live:
        return order, False

    order.rider = offer.rider
    order.save(update_fields=["rider", "updated_at"])
    offer.state = DeliveryOffer.State.ACCEPTED
    offer.responded_at = timezone.now()
    offer.save(update_fields=["state", "responded_at", "updated_at"])

    notify(order.customer, f"Order {order.order_code}",
           f"{offer.rider.name} will deliver your order 🛵", order.order_code)
    return order, True


@transaction.atomic
def decline_offer(offer):
    """A rider passes. Close the offer and immediately try the next rider."""
    if offer.state == DeliveryOffer.State.OFFERED:
        offer.state = DeliveryOffer.State.REJECTED
        offer.responded_at = timezone.now()
        offer.save(update_fields=["state", "responded_at", "updated_at"])
    return offer_order(offer.order)


@transaction.atomic
def assign_rider(order, rider):
    """Admin override: put a specific rider on the order, whatever the offers say.

    Any live offer is closed — an admin decision is final, and leaving a live
    offer out would let a second rider accept the same order.
    """
    order = FoodOrder.objects.select_for_update().get(pk=order.pk)
    order.rider = rider
    order.save(update_fields=["rider", "updated_at"])
    order.delivery_offers.filter(state=DeliveryOffer.State.OFFERED).update(
        state=DeliveryOffer.State.EXPIRED, responded_at=timezone.now())
    notify(order.customer, f"Order {order.order_code}",
           f"{rider.name} will deliver your order 🛵", order.order_code)
    notify(rider.user, f"New delivery {order.order_code}",
           f"Pick up from {order.restaurant.name} 🛵", order.order_code)
    return order


def sweep_offers():
    """Expire timed-out offers and cascade every stuck order to the next rider.

    This is what keeps the cycle moving without a job runner. It is called
    opportunistically — whenever a rider polls their offers, and by the
    `sweep_delivery_offers` management command for a cron where one is available.
    With several riders each polling every few seconds, an expired offer is
    picked up within seconds in practice; the command is the backstop for the
    case where the offered rider went offline and stopped polling.

    Returns (expired_count, re_offered_count).
    """
    now = timezone.now()
    expired = DeliveryOffer.objects.filter(
        state=DeliveryOffer.State.OFFERED, expires_at__lte=now)
    expired_count = expired.count()

    # Every offerable order with no live offer needs a (re-)offer: those whose
    # offer just expired, and any that never got one because no rider was online
    # when they were confirmed.
    expired.update(state=DeliveryOffer.State.EXPIRED, responded_at=now)

    stuck = (FoodOrder.objects.filter(status__in=OFFERABLE_STATUSES, rider__isnull=True)
             .exclude(delivery_offers__state=DeliveryOffer.State.OFFERED)
             .distinct())
    re_offered = 0
    for order in stuck:
        if offer_order(order) is not None:
            re_offered += 1
    return expired_count, re_offered


def live_offer_for_rider(rider):
    """The single offer this rider should be answering right now, if any.

    Sweeps first so a rider never sees an offer that has already timed out.
    """
    sweep_offers()
    return (DeliveryOffer.objects.filter(rider=rider, state=DeliveryOffer.State.OFFERED)
            .select_related("order", "order__restaurant").order_by("offered_at").first())
