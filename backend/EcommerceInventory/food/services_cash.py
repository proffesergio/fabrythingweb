"""Rider cash: what a rider is holding, and letting them hand it back.

The model is "the rider is a courier of money, not a party to it". On a COD
order the customer's cash goes to the rider, the rider deposits it with the
platform, and the platform pays the restaurant and the rider on their own
cycles. That is what keeps commission from ever needing to be invoiced.

The risk it creates is float sitting in riders' pockets. That risk is bounded
here, by one number and one filter:

  cash_in_hand(rider)  — derived from settlement legs, never stored
  over_ceiling(rider)  — stops offering COD orders past a limit

`cash_in_hand` is derived on purpose. A stored balance column would need a
correct increment at delivery and a correct decrement at deposit, and any missed
write would silently misstate what a rider owes. Deriving it from the ledger
means the two cannot disagree.
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from food.models import DeliveryPricing, OrderSettlement, Rider, RiderCashDeposit

ZERO = Decimal("0.00")
CENTS = Decimal("0.01")


def _q(value):
    """Money is always two places. Sum() over an empty or integral set returns
    an unquantized Decimal, which would render as "500" in the API."""
    return Decimal(value or 0).quantize(CENTS)


def collected_total(rider):
    """Every taka this rider has collected on delivered COD orders.

    A PENDING `rider_cash` leg means the money reached the rider and has not
    come back. NA means there was nothing to collect (a prepaid order), and
    SETTLED means an earlier deposit already covered it — but deposits are
    recorded as *amounts*, not per-order, so the outstanding figure is
    collections minus deposits rather than a sum over pending legs alone.
    """
    total = (OrderSettlement.objects
             .filter(rider=rider)
             .exclude(rider_cash_status=OrderSettlement.Settle.NA)
             .aggregate(s=Sum("order__total"))["s"])
    return _q(total)


def deposited_total(rider):
    total = RiderCashDeposit.objects.filter(rider=rider).aggregate(s=Sum("amount"))["s"]
    return _q(total)


def cash_in_hand(rider):
    """What this rider still owes the platform. Never negative — an
    over-deposit (a rider paying a round number) is a credit, not a debt."""
    return _q(max(collected_total(rider) - deposited_total(rider), ZERO))


def over_ceiling(rider, config=None):
    """Is this rider holding too much of our money to be given more?

    This is the actual protection against rider default; the reporting around it
    is just visibility. A rider over the line keeps working — they simply stop
    being offered *cash* orders until they deposit.
    """
    cfg = config or DeliveryPricing.get_solo()
    return cash_in_hand(rider) >= Decimal(cfg.rider_cash_ceiling)


def riders_over_ceiling(config=None):
    """Ids of riders currently over the limit, for the dispatch filter.

    Computed in Python over the rider set rather than as one SQL expression:
    the rider table is small (a village operation, tens of riders), and the
    derivation reads clearly. Revisit if that stops being true.
    """
    cfg = config or DeliveryPricing.get_solo()
    return {r.id for r in Rider.objects.all() if over_ceiling(r, cfg)}


@transaction.atomic
def record_deposit(rider, amount, *, received_by=None, note=""):
    """Record cash handed back, and settle the legs it covers.

    Oldest first: a rider's outstanding balance should age out in the order it
    was collected, so a partial deposit clears the oldest debt rather than an
    arbitrary one.
    """
    amount = Decimal(str(amount))
    if amount <= ZERO:
        raise ValueError("A deposit must be a positive amount.")

    deposit = RiderCashDeposit.objects.create(
        rider=rider, amount=amount, received_by=received_by, note=note)

    remaining = amount
    pending = (OrderSettlement.objects
               .filter(rider=rider, rider_cash_status=OrderSettlement.Settle.PENDING)
               .select_related("order").order_by("created_at"))
    for settlement in pending:
        if remaining <= ZERO:
            break
        owed = Decimal(settlement.order.total)
        # Only a leg fully covered is marked settled. Marking a partly-covered
        # leg would overstate what has come back.
        if remaining >= owed:
            from food.services_settlement import settle_leg
            settle_leg(settlement, "rider_cash", settled=True)
            remaining -= owed

    return deposit


def rider_cash_summary(rider):
    return {
        "rider_id": rider.id,
        "rider_name": rider.name,
        "collected": str(collected_total(rider)),
        "deposited": str(deposited_total(rider)),
        "cash_in_hand": str(cash_in_hand(rider)),
        "over_ceiling": over_ceiling(rider),
    }
