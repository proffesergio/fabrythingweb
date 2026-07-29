"""Platform-revenue markup on product prices -- the single definition of what
a customer pays on top of a product's supplier/source price.

One rule lives here and nowhere else, the same shape as the commission rule
in ``food/pricing.py``:

    markup       = max(markup_floor, base_price * markup_percentage / 100)
    selling_price = base_price + markup

A flat percentage loses money on a cheap item (3% of a 99 BDT item is under
3 taka) and a flat floor gives up all upside on an expensive one (a flat 100
BDT is 0.01% margin on a 989,900 BDT laptop) -- the live catalog runs both
ends of that range, so neither alone works. ``max()`` gets both: a guaranteed
minimum margin on cheap items that scales on expensive ones.

Configuration (``markup_percentage``, ``markup_floor``) lives on
``core.models.StoreConfiguration`` (the ``get_solo()`` singleton, admin
editable, no redeploy needed) rather than an env var or a hardcoded constant --
same reasoning as ``food.models.DeliveryPricing``.

**Idempotency is the whole point of this module.** Every caller must derive
the selling price from a stored, never-mutated ``Products.base_price`` --
never from the current ``initial_selling_price``. Calling ``apply_markup``
again on an already-marked-up selling price would stack a second markup on
top of the first; calling it on ``base_price`` again always reproduces the
exact same number. See ``catalog/management/commands/apply_pricing_markup.py``
and ``catalog/services_price_sync.py`` for the two places that matters most.
"""
from decimal import Decimal, ROUND_HALF_UP

from core.models import StoreConfiguration

CENTS = Decimal("0.01")


def _q(value):
    return Decimal(str(value)).quantize(CENTS, rounding=ROUND_HALF_UP)


def markup_for(base_price, *, floor=None, percentage=None, config=None):
    """The markup (in taka) on one product's base (pre-markup) price.

    ``max(floor, base_price * percentage%)`` -- mirrors
    ``food.pricing.commission_for``. Returns ``None`` for a ``None``
    base_price (nothing to mark up), so callers can pass a possibly-absent
    discount straight through without a separate null check.
    """
    if base_price is None:
        return None
    cfg = config or StoreConfiguration.get_solo()
    base = Decimal(str(base_price))
    floor_v = Decimal(str(floor if floor is not None else cfg.markup_floor))
    pct = Decimal(str(percentage if percentage is not None else cfg.markup_percentage))
    by_percentage = _q(base * pct / Decimal("100"))
    return max(_q(floor_v), by_percentage)


def apply_markup(base_price, *, floor=None, percentage=None, config=None):
    """The selling price for one base (pre-markup) price: ``base_price +
    markup_for(base_price)``.

    This is the ONLY function that should ever compute a selling price from a
    base price. Every path that sets a marked-up price -- product import,
    ``seed_store_catalog``, ``sync_source_prices``, the retroactive
    ``apply_pricing_markup`` backfill -- must call this on ``base_price``,
    never on the current ``initial_selling_price``, or the markup stacks on
    every re-run.

    Returns ``None`` for a ``None`` base_price (nothing to sell), and a
    ``float`` otherwise to match ``Products.initial_selling_price`` /
    ``discount_price``, which are plain ``FloatField``s.
    """
    if base_price is None:
        return None
    base = Decimal(str(base_price))
    markup = markup_for(base_price, floor=floor, percentage=percentage, config=config)
    return float(_q(base + markup))
