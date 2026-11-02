"""Re-price partner-sourced products from their live pages.

Products with a source_url came from the partner computer stores
(potakait.com / canvasit.com.bd -- see the 2026-07-27 spec: explicit reseller
permission). The partner's live retail price becomes this product's
``base_price``, and the selling price is re-derived from it through
``catalog.pricing.apply_markup`` -- the same single markup rule every other
price-setting path in the catalog uses (import, ``seed_store_catalog``, the
``apply_pricing_markup`` backfill, the admin quick-update endpoint).

This used to apply its own second markup here via a ``RESELLER_MARKUP_PERCENT``
env var (``factor = 1 + markup_percent/100``). That is retired: once
``apply_markup`` existed as the one platform-revenue rule, keeping this env-var
factor around would have marked up partner products TWICE (once here, once
wherever else applied the unified markup) -- exactly the double-markup bug
this feature was built to avoid. See docs/PRICING_MARKUP.md.

Only products with a non-empty source_url are ever touched here -- Fabrilife
and hand-entered products are excluded by the queryset filter below, not by
any per-product check, so there is no way for a blank source_url to slip
through and get re-priced.
"""
from django.utils import timezone
from django.db import transaction

from catalog.models import Products
from catalog.pricing import apply_markup, quote_supplier_price
from catalog.scrape_parsers import parse_opencart_product
from catalog.supplier_security import supplier_get, validate_supplier_url


def _default_fetcher(url):
    import time
    time.sleep(1)
    return supplier_get(url)


def sync_source_prices(fetcher=None, dry_run=False, source=None, limit=None, pricing_policy=None,
                       after_id=0):
    """Re-fetch each source_url product's live partner page, treat its retail
    price as the new ``base_price``, and re-derive the selling price (and
    discount price, if any) through ``apply_markup``.

    Returns a list of dicts, one per product with a non-empty source_url:
    {"slug", "old_price", "new_price", "old_discount", "new_discount",
    "updated"}. A per-product fetch/parse failure is recorded as
    updated=False and the run continues -- one dead partner page must not
    stop the rest of the sync.
    """
    fetch = fetcher or _default_fetcher
    changes = []
    queryset = Products.objects.exclude(source_url="").order_by('id')
    if source is not None:
        queryset = queryset.filter(source_url__startswith=source.base_url.rstrip('/') + '/')
    if after_id:
        later = queryset.filter(id__gt=after_id)
        queryset = later if later.exists() else queryset
    if limit is not None:
        queryset = queryset[:limit]
    for p in queryset.iterator():
        rec = {"product_id": p.id, "slug": p.slug, "old_price": p.initial_selling_price,
               "new_price": None, "old_discount": p.discount_price,
               "new_discount": None, "updated": False}
        policy_currency = (pricing_policy or {}).get('source_currency', 'BDT')
        # A changed policy must not reinterpret a supplier's raw amount in a
        # different currency: that can silently underprice checkout variants.
        if p.source_currency != policy_currency:
            changes.append(rec)
            continue
        try:
            if source is not None:
                validate_supplier_url(p.source_url, source)
            parsed = parse_opencart_product(fetch(p.source_url))
        except Exception:  # noqa: BLE001 -- one dead page must not stop the run
            changes.append(rec)
            continue
        price = parsed.get("price")
        if not price:
            changes.append(rec)
            continue
        try:
            quote = quote_supplier_price(price, pricing_policy,
                weight_grams=int(p.weight * 1000) if p.weight is not None else None)
        except ValueError:
            changes.append(rec)
            continue
        new_base = quote['base_price']
        new_selling = quote['selling_price']
        disc = parsed.get("discount_price")
        try:
            new_discount = quote_supplier_price(disc, pricing_policy,
                weight_grams=int(p.weight * 1000) if p.weight is not None else None)['selling_price'] if disc else None
        except ValueError:
            changes.append(rec)
            continue
        rec["new_price"], rec["new_discount"] = new_selling, new_discount
        if not dry_run:
            with transaction.atomic():
                p.base_price = new_base
                p.initial_selling_price = new_selling
                p.discount_price = new_discount
                p.source_price = price
                if pricing_policy:
                    p.source_currency = quote['source_currency']
                p.price_synced_at = timezone.now()
                p.save(update_fields=["base_price", "initial_selling_price", "discount_price",
                                      "source_price", "source_currency", "price_synced_at", "updated_at"])
                # Checkout charges active variants; commit both prices together.
                p.variants.filter(is_active=True).update(
                    price=new_selling, discount_price=new_discount)
        rec["updated"] = True
        changes.append(rec)
    return changes
