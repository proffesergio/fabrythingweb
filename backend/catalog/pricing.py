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
from decimal import Decimal, ROUND_HALF_UP, ROUND_CEILING, InvalidOperation

from core.models import StoreConfiguration
from django.utils import timezone
from datetime import datetime

CENTS = Decimal("0.01")


def _q(value):
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0:
            raise ValueError('Price must be finite and non-negative.')
        return amount.quantize(CENTS, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError) as exc:
        raise ValueError('Price must be a valid decimal amount.') from exc


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
    if not base.is_finite() or base <= 0 or not floor_v.is_finite() or floor_v < 0 or not pct.is_finite() or pct < 0:
        raise ValueError('Price and markup configuration must be finite and non-negative.')
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


def quote_supplier_price(source_price, policy, *, weight_grams=None):
    """Convert supplier cost to BDT and enforce shipping, fees, and margin."""
    if not policy:
        selling = apply_markup(source_price)
        if _q(selling) > Decimal('99999999.99'):
            raise ValueError('Selling price exceeds the variant field limit.')
        return {'base_price': float(_q(source_price)),
                'selling_price': selling, 'shipping_fee': None}
    currency = policy.get('source_currency', 'BDT')
    if not isinstance(currency, str) or len(currency) != 3 or not currency.isalpha() or not currency.isupper():
        raise ValueError('source_currency must be a three-letter uppercase code.')
    amount = _q(source_price)
    if amount <= 0:
        raise ValueError('Supplier price must be positive.')
    rate = Decimal('1')
    if currency != 'BDT':
        try:
            rate = Decimal(str(policy['fx_rate_to_bdt']))
            observed = datetime.fromisoformat(policy['fx_rate_observed_at'].replace('Z', '+00:00'))
            max_age = int(policy.get('fx_max_age_hours', 24))
        except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
            raise ValueError('A dated FX rate is required for foreign currency.') from exc
        if observed.tzinfo is None:
            raise ValueError('FX rate timestamp must include a timezone.')
        age = timezone.now() - observed
        if not 1 <= max_age <= 168 or age.total_seconds() < 0 or age.total_seconds() > max_age * 3600:
            raise ValueError('FX rate is stale, future-dated, or missing a timezone.')
        if not rate.is_finite() or rate <= 0:
            raise ValueError('FX rate must be positive and finite.')
    def percent(key):
        try:
            value = Decimal(str(policy.get(key, 0)))
        except (InvalidOperation, TypeError) as exc:
            raise ValueError(f'{key} must be a valid percentage.') from exc
        if not value.is_finite() or value < 0 or value >= 100:
            raise ValueError(f'{key} must be between 0 and 100.')
        return value
    fee = percent('fee_percent')
    margin = percent('target_margin_percent')
    if fee + margin >= 100:
        raise ValueError('Fee and target margin must total less than 100%.')
    shipping_base = _q(policy.get('shipping_base_bdt', 0))
    shipping_per_kg = _q(policy.get('shipping_per_kg_bdt', 0))
    weight = weight_grams if weight_grams is not None else policy.get('weight_grams')
    if shipping_per_kg and weight is None:
        raise ValueError('Weight is required for per-kg shipping.')
    try:
        weight_value = Decimal(str(weight or 0))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError('Weight must be numeric.') from exc
    if not weight_value.is_finite() or weight_value < 0 or weight_value > 100000:
        raise ValueError('Weight must be between 0 and 100000 grams.')
    shipping = _q(shipping_base + shipping_per_kg * weight_value / Decimal('1000'))
    cost_bdt = _q(amount * rate)
    # Checkout may waive shipping or collect it only once for a multi-item
    # cart, so do not count any customer shipping as guaranteed revenue.
    from core.models import StoreConfiguration
    absolute_floor = _q(StoreConfiguration.get_solo().markup_floor)
    target_gross = (cost_bdt + shipping + absolute_floor) / (
        Decimal('1') - (fee + margin) / Decimal('100'))
    target_item = target_gross.quantize(CENTS, rounding=ROUND_CEILING)
    selling = max(_q(apply_markup(cost_bdt)), target_item)
    if selling > Decimal('99999999.99'):
        raise ValueError('Selling price exceeds the variant field limit.')
    return {'base_price': float(cost_bdt), 'selling_price': float(selling),
            'shipping_cost': shipping, 'shipping_fee': None,
            'weight_grams': int(weight_value),
            'source_currency': currency}
