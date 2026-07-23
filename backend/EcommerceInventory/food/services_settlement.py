"""Turn a delivered order into a settlement row: who is owed what, and by whom.

Called once, when an order reaches DELIVERED. Every rate is read here and then
frozen onto the row — see the OrderSettlement docstring for why.
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from food.models import FoodOrder, OrderSettlement
from food.pricing import commission_for

CENTS = Decimal("0.01")

# Flat per-delivery pay. Mirrors RIDER_BASE_PAY in views_food_ext (the rider
# dashboard's own earnings record) — keep the two in step, or a rider's dashboard
# total will drift from what the settlement ledger says we owe them.
DEFAULT_RIDER_BASE_PAY = Decimal("40.00")


def _q(value):
    return Decimal(value).quantize(CENTS)


def _base_pay_for(order, override=None):
    """What we owe the rider for the distance, in priority order.

    The order's own `rider_base_pay` is the number quoted and shown at checkout,
    snapshotted with the distance it was derived from — it is the honest answer
    and it wins. An explicit override (a caller correcting a settlement) beats
    it; the flat default is only for orders placed before distance pricing, whose
    snapshot is 0.
    """
    if not order.rider:
        # Nobody delivered it (self-pickup, or admin closed it out) — no rider leg.
        return Decimal("0.00")
    if override is not None:
        return Decimal(override)
    quoted = Decimal(order.rider_base_pay or 0)
    return quoted if quoted > 0 else DEFAULT_RIDER_BASE_PAY


def compute_breakdown(order, rider_base_pay=None):
    """Pure money math for one order. No DB writes — safe to call for previews.

    The coupon discount is borne by the restaurant: it comes off `food_net`
    before commission, so the platform takes its cut of the discounted price,
    not the menu price.

    Commission is `max(floor, rate%)`, capped at food_net — see
    food.pricing.commission_for. Both the rate and the floor are returned so the
    settlement row can snapshot them.
    """
    base_pay = _base_pay_for(order, rider_base_pay)

    rate = order.restaurant.commission_percentage
    floor = order.restaurant.min_commission_amount
    food_net = _q(max(order.subtotal - order.discount, Decimal("0.00")))
    commission = commission_for(order.restaurant, food_net, floor=floor, rate=rate)
    restaurant_payout = _q(food_net - commission)
    rider_payout = _q(base_pay + order.tip)
    platform_revenue = _q(commission + order.delivery_fee - base_pay)

    return {
        "commission_rate": _q(rate),
        "commission_floor": _q(floor),
        "food_net": food_net,
        "delivery_fee": _q(order.delivery_fee),
        "tip": _q(order.tip),
        "commission_amount": commission,
        "restaurant_payout": restaurant_payout,
        "rider_base_pay": _q(base_pay),
        "rider_payout": rider_payout,
        "platform_revenue": platform_revenue,
    }


@transaction.atomic
def settle_order(order, rider_base_pay=None):
    """Create (or return) the settlement for a delivered order.

    Idempotent: replaying a DELIVERED transition must not double-book the money.
    """
    existing = OrderSettlement.objects.filter(order=order).first()
    if existing:
        return existing

    breakdown = compute_breakdown(order, rider_base_pay=rider_base_pay)

    # A non-COD order was already paid online, so there is no cash for the rider
    # to hand over and nothing to collect on delivery.
    is_cod = (order.payment_method or "COD").upper() == "COD"
    now = timezone.now()

    return OrderSettlement.objects.create(
        order=order,
        rider=order.rider,
        rider_name=order.rider.name if order.rider else "",
        customer_payment_status=(OrderSettlement.Settle.PENDING if is_cod
                                 else OrderSettlement.Settle.SETTLED),
        customer_payment_at=None if is_cod else now,
        rider_cash_status=(OrderSettlement.Settle.PENDING if is_cod and order.rider
                           else OrderSettlement.Settle.NA),
        rider_payout_status=(OrderSettlement.Settle.PENDING if order.rider
                             else OrderSettlement.Settle.NA),
        restaurant_payout_status=OrderSettlement.Settle.PENDING,
        **breakdown,
    )


def settle_leg(settlement, leg, settled=True, user=None):
    """Mark one settlement leg (see OrderSettlement.LEGS) settled or back to pending."""
    if leg not in OrderSettlement.LEGS:
        raise ValueError(f"Unknown settlement leg: {leg}")
    status_field, at_field = OrderSettlement.LEGS[leg]

    # An NA leg has no money in it — don't let the UI flip it into the books.
    if getattr(settlement, status_field) == OrderSettlement.Settle.NA:
        return settlement

    setattr(settlement, status_field,
            OrderSettlement.Settle.SETTLED if settled else OrderSettlement.Settle.PENDING)
    setattr(settlement, at_field, timezone.now() if settled else None)
    settlement.save(update_fields=[status_field, at_field, "updated_at"])

    # Keep the order's own payment flag in step with the ledger, so the rider
    # dashboard's "cash to collect" and the customer's order view agree.
    if leg == "customer_payment":
        order = settlement.order
        order.payment_status = "COLLECTED" if settled else "PENDING"
        order.save(update_fields=["payment_status", "updated_at"])

    return settlement


def backfill_settlements(rider_base_pay=None):
    """Create settlements for delivered orders that predate this ledger.

    Returns the number created. Safe to re-run — settle_order is idempotent.
    """
    delivered = (FoodOrder.objects.filter(status=FoodOrder.Status.DELIVERED,
                                          settlement__isnull=True)
                 .select_related("restaurant", "rider"))
    created = 0
    for order in delivered:
        settle_order(order, rider_base_pay=rider_base_pay)
        created += 1
    return created
