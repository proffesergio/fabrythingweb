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

from catalog.models import Products
from catalog.pricing import apply_markup
from catalog.scrape_parsers import parse_opencart_product


def _default_fetcher(url):
    import requests
    r = requests.get(url, timeout=20,
                     headers={"User-Agent": "Mozilla/5.0 (fabrything price sync)"})
    r.raise_for_status()
    return r.text


def sync_source_prices(fetcher=None, dry_run=False):
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
    for p in Products.objects.exclude(source_url="").iterator():
        rec = {"slug": p.slug, "old_price": p.initial_selling_price,
               "new_price": None, "old_discount": p.discount_price,
               "new_discount": None, "updated": False}
        try:
            parsed = parse_opencart_product(fetch(p.source_url))
        except Exception:  # noqa: BLE001 -- one dead page must not stop the run
            changes.append(rec)
            continue
        price = parsed.get("price")
        if not price:
            changes.append(rec)
            continue
        new_base = price
        new_selling = apply_markup(new_base)
        disc = parsed.get("discount_price")
        new_discount = apply_markup(disc) if disc else None
        rec["new_price"], rec["new_discount"] = new_selling, new_discount
        if not dry_run:
            p.base_price = new_base
            p.initial_selling_price = new_selling
            p.discount_price = new_discount
            p.source_price = price
            p.price_synced_at = timezone.now()
            p.save(update_fields=["base_price", "initial_selling_price", "discount_price",
                                  "source_price", "price_synced_at", "updated_at"])
            # Checkout charges the VARIANT, not Products (orders/services.py
            # snapshots unit_price from ProductVariant.effective_price) -- so
            # a product and its variants must never disagree on price. These
            # variants were created by our own seeder mirroring the partner
            # price, so mirroring the new price/discount forward onto them
            # here is correct. Only active variants: an inactive/retired SKU
            # is not sellable and re-pricing it is not observable anyway.
            p.variants.filter(is_active=True).update(
                price=new_selling, discount_price=new_discount)
        rec["updated"] = True
        changes.append(rec)
    return changes
