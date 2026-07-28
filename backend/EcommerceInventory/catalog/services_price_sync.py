"""Re-price partner-sourced products from their live pages.

Products with a source_url came from the partner computer stores
(potakait.com / canvasit.com.bd -- see the 2026-07-27 spec: explicit reseller
permission). Selling price mirrors their retail price plus an optional
markup; dealer margin is the difference the owner negotiates offline.

Only products with a non-empty source_url are ever touched here -- Fabrilife
and hand-entered products are excluded by the queryset filter below, not by
any per-product check, so there is no way for a blank source_url to slip
through and get re-priced.
"""
import os

from django.utils import timezone

from catalog.models import Products
from catalog.scrape_parsers import parse_opencart_product


def _default_fetcher(url):
    import requests
    r = requests.get(url, timeout=20,
                     headers={"User-Agent": "Mozilla/5.0 (fabrything price sync)"})
    r.raise_for_status()
    return r.text


def sync_source_prices(fetcher=None, dry_run=False, markup_percent=None):
    """Re-fetch each source_url product's live partner page and mirror its
    retail price (plus an optional markup) onto our product.

    Returns a list of dicts, one per product with a non-empty source_url:
    {"slug", "old_price", "new_price", "old_discount", "new_discount",
    "updated"}. A per-product fetch/parse failure is recorded as
    updated=False and the run continues -- one dead partner page must not
    stop the rest of the sync.
    """
    fetch = fetcher or _default_fetcher
    if markup_percent is None:
        markup_percent = float(os.environ.get("RESELLER_MARKUP_PERCENT", "0"))
    factor = 1 + markup_percent / 100.0
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
        new_price = round(price * factor, 2)
        disc = parsed.get("discount_price")
        new_disc = round(disc * factor, 2) if disc else None
        rec["new_price"], rec["new_discount"] = new_price, new_disc
        if not dry_run:
            p.initial_selling_price = new_price
            p.discount_price = new_disc
            p.source_price = price
            p.price_synced_at = timezone.now()
            p.save(update_fields=["initial_selling_price", "discount_price",
                                  "source_price", "price_synced_at", "updated_at"])
            # Checkout charges the VARIANT, not Products (orders/services.py
            # snapshots unit_price from ProductVariant.effective_price) -- so
            # a product and its variants must never disagree on price. These
            # variants were created by our own seeder mirroring the partner
            # price, so mirroring the new price/discount forward onto them
            # here is correct. Only active variants: an inactive/retired SKU
            # is not sellable and re-pricing it is not observable anyway.
            p.variants.filter(is_active=True).update(
                price=new_price, discount_price=new_disc)
        rec["updated"] = True
        changes.append(rec)
    return changes
