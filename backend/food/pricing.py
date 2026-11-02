"""Delivery pricing and commission — the single definition of what an order costs.

Two rules live here and nowhere else:

1. **Commission is `max(floor, percentage)`.** A flat percentage loses money on
   small rural baskets; a flat fee gives up all upside on large ones.
2. **Delivery is priced by distance, and the platform never pays out more
   delivery money than it took in.** That guarantee is enforced structurally by
   `delivery_quote`, not by choosing the rates carefully — see
   `_apply_margin_backstop`.

Everything returned here is *quoted*, then snapshotted onto the order at
checkout. Settlement reads the snapshot, never these functions, so changing a
rate tomorrow cannot move yesterday's books.
"""
from decimal import Decimal, ROUND_HALF_UP, ROUND_UP

from rest_framework.exceptions import ValidationError

from food.geo import haversine_km
from food.models import DeliveryPricing, RestaurantZone

CENTS = Decimal("0.01")


def _q(value):
    return Decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP)


def _round_up_to(amount, step):
    """Round a fee UP to the next multiple of `step` (0/1 disables rounding).

    Up, not nearest: this is the customer-facing fee in a cash economy, and
    rounding it down is the platform paying for change out of its margin.
    """
    step = int(step or 0)
    if step <= 1:
        return _q(amount)
    stepd = Decimal(step)
    return _q((Decimal(amount) / stepd).quantize(Decimal("1"), rounding=ROUND_UP) * stepd)


def commission_for(restaurant, food_net, *, floor=None, rate=None):
    """Platform commission on one order's food value.

    `food_net` is subtotal minus discount — the discount is borne by the
    restaurant, so commission is taken on what the customer actually paid for
    food, not the menu price.

    Capped at `food_net`: on a ৳20 order the ৳25 floor would otherwise produce a
    negative restaurant payout, i.e. the platform billing a restaurant for the
    privilege of selling something. The floor takes everything, but never more.
    """
    food_net = _q(max(Decimal(food_net), Decimal("0.00")))
    rate = Decimal(rate if rate is not None else restaurant.commission_percentage)
    floor = Decimal(floor if floor is not None else restaurant.min_commission_amount)
    by_rate = _q(food_net * rate / Decimal("100"))
    return min(max(by_rate, _q(floor)), food_net)


def _destination_point(*, zone, village, lat, lng):
    """Where we believe the food is going, best source first.

    A dropped pin is the truth. Failing that a village centre, failing that the
    zone centre — each step less precise, and the last one can be a couple of km
    out inside a large union, which is why `distance_km` records what we used.
    """
    if lat is not None and lng is not None:
        return Decimal(str(lat)), Decimal(str(lng)), "pin"
    if village and village.center_lat is not None and village.center_lng is not None:
        return village.center_lat, village.center_lng, "village"
    if zone and zone.center_lat is not None and zone.center_lng is not None:
        return zone.center_lat, zone.center_lng, "zone"
    return None, None, "unknown"


def distance_for(restaurant, *, zone=None, village=None, lat=None, lng=None):
    """Straight-line km from the restaurant to the delivery point, or None.

    None is a real answer: a restaurant with no pickup pin, or a delivery with
    no usable destination, cannot be priced by distance and falls back to the
    flat per-zone fee. Mirrors the frontend's `km()` in FoodLocationContext.
    """
    if restaurant.pickup_lat is None or restaurant.pickup_lng is None:
        return None, "no-pickup-pin"
    dlat, dlng, source = _destination_point(zone=zone, village=village, lat=lat, lng=lng)
    if dlat is None:
        return None, source
    km = haversine_km(restaurant.pickup_lat, restaurant.pickup_lng, dlat, dlng)
    return Decimal(str(round(km, 2))), source


def flat_fee_for(restaurant, zone):
    """The pre-distance fee: a per-restaurant-per-zone override, else the
    restaurant's own base. Still the answer whenever distance is unknown."""
    rz = RestaurantZone.objects.filter(restaurant=restaurant, zone=zone).first()
    if rz and rz.delivery_fee is not None:
        return _q(rz.delivery_fee)
    return _q(restaurant.base_delivery_fee)


def _apply_margin_backstop(fee, rider_pay, min_margin):
    """Never pay a rider more delivery money than we collected.

    `platform_revenue = commission + delivery_fee - rider_base_pay`, so a rider
    payment above `fee - min_margin` turns delivery into a subsidy funded out of
    commission. Rates are *meant* to be set so this never binds (per_km_fee >
    rider_per_km); this exists so that a misconfiguration in the admin panel
    costs the platform nothing.

    It binds legitimately in one place: a flat per-zone override that is smaller
    than distance-based rider pay. The rider is capped, not the platform — which
    is precisely why `max_delivery_km` refuses the orders where that cap would
    be unfair rather than letting it bite.
    """
    ceiling = max(_q(fee) - _q(min_margin), Decimal("0.00"))
    return min(_q(rider_pay), ceiling)


def delivery_quote(restaurant, *, zone=None, village=None, lat=None, lng=None, config=None,
                   enforce_range=True):
    """Price one delivery.

    Returns everything the order needs to snapshot:
        {fee, rider_base_pay, distance_km, distance_source, platform_margin, priced_by}

    Raises ValidationError when the destination is beyond `max_delivery_km` —
    better an honest refusal at checkout than a delivery nobody is paid properly
    for. Pass `enforce_range=False` for previews that want to show the reason.
    """
    cfg = config or DeliveryPricing.get_solo()
    distance, source = distance_for(restaurant, zone=zone, village=village, lat=lat, lng=lng)

    if distance is None:
        # Unknown distance → today's behaviour exactly: the flat per-zone fee,
        # and the rider's flat base pay.
        fee = flat_fee_for(restaurant, zone)
        rider_pay = _apply_margin_backstop(fee, cfg.rider_base_pay, cfg.platform_min_margin)
        return {
            "fee": fee, "rider_base_pay": rider_pay, "distance_km": None,
            "distance_source": source, "priced_by": "flat",
            "platform_margin": _q(fee - rider_pay),
        }

    if enforce_range and distance > Decimal(cfg.max_delivery_km):
        raise ValidationError(
            f"That address is {distance} km away — beyond our {cfg.max_delivery_km} km "
            f"delivery range for this restaurant.")

    # An explicit per-zone override is a deliberate commercial decision (a promo
    # rate, say) and outranks the distance formula. The rider is still paid by
    # distance, subject to the backstop.
    rz = RestaurantZone.objects.filter(restaurant=restaurant, zone=zone).first()
    override = rz.delivery_fee if rz and rz.delivery_fee is not None else None

    billable_km = max(Decimal("0.00"), distance - Decimal(cfg.free_km))
    if override is not None:
        fee = _q(override)
        priced_by = "zone-override"
    else:
        raw = Decimal(cfg.base_fee) + Decimal(cfg.per_km_fee) * billable_km
        fee = _round_up_to(raw, cfg.round_to_nearest)
        fee = min(max(fee, _q(cfg.min_fee)), _q(cfg.max_fee))
        priced_by = "distance"

    rider_pay = Decimal(cfg.rider_base_pay) + Decimal(cfg.rider_per_km) * billable_km
    rider_pay = _apply_margin_backstop(fee, rider_pay, cfg.platform_min_margin)

    return {
        "fee": fee, "rider_base_pay": rider_pay, "distance_km": _q(distance),
        "distance_source": source, "priced_by": priced_by,
        "platform_margin": _q(fee - rider_pay),
    }
