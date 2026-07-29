"""Backfill catalog.Products.size_chart for the already-seeded Fabrilife
fashion products.

The 64 Fabrilife products in catalog/fixtures/seed/fabrilife_fashion.json
were scraped before catalog.scrape_parsers learned to read a size chart, so
every one of them carries size_chart={} regardless of whether the live
fabrilife.com product actually has one. `parse_fabrilife_product` (and the
one-time offline `tools/scrape/scrape_fabrilife.py`) now capture it for any
*future* (re-)scrape, but that does nothing for rows already in the
database -- this module is the one-time retrofit for those.

Fabrilife products deliberately carry no `source_url` (see CLAUDE.md's
"Store catalog seeding" note and the module docstring on
catalog/scrape_parsers.py: fabrilife.com is a one-time seed source, not a
reseller partner enrolled in source_url price-sync), so unlike
`sync_source_prices` there is no stored URL to refetch directly. Instead
each candidate product is looked up by exact name against fabrilife.com's
own public, search-only Algolia `products` index -- the same endpoint
`parse_fabrilife_listing` / `tools/scrape/scrape_fabrilife.py` already read
for category listings -- and its `size_chart` is read straight off the
search hit via `parse_fabrilife_algolia_size_chart`. Confirmed live
(2026-07-29): a hit carries a structured `size_chart` field already, so this
needs no second fetch+parse of the rendered product page HTML at all.

A hit only counts as a match when its `title` equals the product's stored
`name` exactly (case-insensitive, whitespace-trimmed). An approximate/fuzzy
match risks silently writing one product's measurements onto a different,
similarly-named product on a live store page -- a wrong chart is worse than
a missing one, so this never guesses: no exact hit, or a hit whose own chart
is empty, is reported and the product is left alone.
"""
import json

from catalog.models import Products
from catalog.scrape_parsers import (
    FABRILIFE_ALGOLIA_APP_ID,
    FABRILIFE_ALGOLIA_SEARCH_KEY,
    FABRILIFE_ALGOLIA_URL,
    parse_fabrilife_algolia_size_chart,
)


def _default_fetcher(name):
    import requests
    headers = {
        "X-Algolia-API-Key": FABRILIFE_ALGOLIA_SEARCH_KEY,
        "X-Algolia-Application-Id": FABRILIFE_ALGOLIA_APP_ID,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (fabrything size-chart backfill)",
    }
    r = requests.post(
        FABRILIFE_ALGOLIA_URL, headers=headers,
        data=json.dumps({"query": name, "hitsPerPage": 3}), timeout=20,
    )
    r.raise_for_status()
    return r.json()


def _candidates():
    """Fabrilife products that have sizes (i.e. are fashion items) but no
    size_chart yet. Filtered in Python rather than a JSONField ORM lookup --
    the candidate set is on the order of 64 rows, not worth pinning to a
    backend-specific empty-dict comparison for."""
    return [
        p for p in Products.objects.filter(brand__iexact="Fabrilife")
        if p.available_sizes and not p.size_chart
    ]


def backfill_fabrilife_size_charts(fetcher=None, dry_run=True):
    """Look up every size-chart-less Fabrilife product by name on
    fabrilife.com's own search and, on an exact title match with a non-empty
    chart, write it onto ``Products.size_chart``.

    Returns a list of per-product dicts:
    ``{"id", "name", "slug", "status", "size_chart"}`` where ``status`` is
    one of:
      - "would_update" / "updated" -- exact title match with a non-empty
        chart (dry_run vs. actually written)
      - "no_match" -- no hit's title equals the product's name exactly
      - "no_chart" -- matched, but that product has no size chart on the
        live site either (not every Fabrilife item carries one)
      - "error" -- the search request itself failed; the run continues

    Never touches any field but ``size_chart`` -- price, images,
    description etc. are left exactly as the admin/seed set them.
    """
    fetch = fetcher or _default_fetcher
    results = []
    for product in _candidates():
        rec = {"id": product.id, "name": product.name, "slug": product.slug,
               "status": "no_match", "size_chart": {}}
        try:
            body = fetch(product.name)
        except Exception:  # noqa: BLE001 -- one dead lookup must not stop the run
            rec["status"] = "error"
            results.append(rec)
            continue

        hit = next(
            (h for h in (body.get("hits") or [])
             if str(h.get("title", "")).strip().lower() == product.name.strip().lower()),
            None,
        )
        if hit is None:
            results.append(rec)
            continue

        chart = parse_fabrilife_algolia_size_chart(hit.get("size_chart"))
        if not chart:
            rec["status"] = "no_chart"
            results.append(rec)
            continue

        rec["size_chart"] = chart
        rec["status"] = "would_update" if dry_run else "updated"
        if not dry_run:
            product.size_chart = chart
            product.save(update_fields=["size_chart", "updated_at"])
        results.append(rec)
    return results
