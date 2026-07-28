"""Offline scrape tool for fabrilife.com -- a one-time seed source for the
Fashion category, NOT a reseller partner. Never imported by Django -- run by
hand under the project venv to produce a JSON fixture that
`catalog.management.commands.seed_store_catalog` loads later.

Unlike tools/scrape/scrape_opencart.py, fixture entries produced here do NOT
carry a `source_url` key: `source_url` exists solely to mark products whose
prices get re-synced from a partner store's live page, and fabrilife.com has
given us no such permission -- these are one-time seed values only.

Usage:

    python tools/scrape/scrape_fabrilife.py catalog/fixtures/seed/fabrilife_fashion.json \
        --limit 10

`--limit` caps products per taxonomy category (the mapping below is fixed,
not CLI-configurable, because it depends on fabrilife.com's own facet
category names -- see FABRILIFE_CATEGORIES).

How listings are fetched (see the module docstring in catalog/scrape_parsers.py
for the full story): fabrilife.com's own `/shop?refinementList[cats][0]=...`
category pages render their product grid client-side via Algolia
InstantSearch -- the raw HTML response contains zero product links in the
results grid. The page's own JS queries Algolia directly with a public
search-only API key embedded in the page source
(`algoliasearch('2UIXGXYA5O', ...)`, index `products`). This tool talks to
that same endpoint the site's own JS uses, and feeds the JSON response into
`parse_fabrilife_listing` (which is typed/named to match the OpenCart listing
parser regardless of the underlying payload format).

Etiquette: one request per second for every network call (listing queries
*and* product page fetches), a real identifying User-Agent, and this is a
one-time capture (not a recurring sync) precisely because fabrilife.com is
not a partner.
"""
import argparse
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # EcommerceInventory/

import requests  # noqa: E402

from catalog.scrape_parsers import parse_fabrilife_listing, parse_fabrilife_product  # noqa: E402
from tools.scrape.common import UA, polite_get, write_fixture  # noqa: E402

BASE_URL = "https://fabrilife.com/"

ALGOLIA_APP_ID = "2UIXGXYA5O"
ALGOLIA_SEARCH_KEY = "bfcfa7b10e2c9220df5d1d639d485218"  # public search-only key, read from the page's own JS
ALGOLIA_INDEX = "products"
ALGOLIA_URL = f"https://{ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/{ALGOLIA_INDEX}/query"

# taxonomy slug (catalog.management.commands.seed_store_catalog.TAXONOMY) ->
# fabrilife.com facet category name(s) (OR'd together within a group).
# Taken from the site's own nav menu (data-cats facet values), verified live.
FABRILIFE_CATEGORIES = {
    "men-tshirts": ["Mens > Half Sleeve T-shirt", "Mens > Full Sleeve T-shirt"],
    "men-polos": ["Mens > Polo T-shirt"],
    "men-panjabi": ["Mens > Panjabi"],
    "men-hoodies": ["Mens > Hoodie", "Mens > Sweatshirt"],
    "women-kurti-tops": ["Womens > Kurti Tunic And Tops"],
    "women-tshirts": ["Womens > T-Shirt"],
    "kids-boys": ["Kids > Boys"],
    "kids-girls": ["Kids > Girls"],
}


def polite_algolia_query(cats, hits_per_page, delay=1.0):
    """POST an Algolia `query` request against fabrilife.com's public
    products index, sleeping `delay` seconds first (same politeness contract
    as tools.scrape.common.polite_get, just POST instead of GET since that's
    what Algolia's query API requires). Returns the raw JSON response body
    (text) so it can be fed straight into parse_fabrilife_listing."""
    time.sleep(delay)
    headers = {
        "X-Algolia-API-Key": ALGOLIA_SEARCH_KEY,
        "X-Algolia-Application-Id": ALGOLIA_APP_ID,
        "Content-Type": "application/json",
        **UA,
    }
    body = {
        "facetFilters": [[f"cats:{c}" for c in cats]],
        "filters": "status:1",
        "hitsPerPage": hits_per_page,
    }
    r = requests.post(headers=headers, url=ALGOLIA_URL, data=json.dumps(body), timeout=20)
    r.raise_for_status()
    return r.text


def scrape(limit):
    entries = []
    for category_slug, cats in FABRILIFE_CATEGORIES.items():
        print(f"[listing] cats={cats} -> {category_slug}")
        listing_json = polite_algolia_query(cats, hits_per_page=limit)
        product_urls = parse_fabrilife_listing(listing_json, BASE_URL)[:limit]
        print(f"  {len(product_urls)} product URL(s)")

        for url in product_urls:
            print(f"  [product] {url}")
            html = polite_get(url)
            p = parse_fabrilife_product(html)
            if not p.get("name") or not p.get("price"):
                print(f"    skipped -- missing name/price for {url}")
                continue
            entries.append({
                "category_path": category_slug,  # a slug from seed_store_catalog TAXONOMY
                "name": p["name"],
                "price": p["price"],
                "discount_price": p.get("discount_price"),
                "description": p.get("description") or p["name"],
                "specifications": p.get("specifications") or {},
                "brand": p.get("brand") or "",
                "images": p["images"][:3],
                "gender": p.get("gender") or "",
                "sizes": p.get("sizes") or [],
                "material": p.get("material") or "",
                # No source_url: fabrilife.com is a one-time seed source, not
                # a reseller partner -- it must not be enrolled in price sync.
            })
    return entries


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out", help="output fixture JSON path")
    parser.add_argument("--limit", type=int, default=10, help="max products per taxonomy category")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    entries = scrape(args.limit)
    write_fixture(args.out, entries)


if __name__ == "__main__":
    main()
