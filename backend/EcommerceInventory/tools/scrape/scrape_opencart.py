"""Offline scrape tool for partner OpenCart stores (potakait.com,
canvasit.com.bd). Never imported by Django -- run by hand under the project
venv to produce a JSON fixture that `catalog.management.commands
.seed_store_catalog` loads later.

Usage:

    python tools/scrape/scrape_opencart.py <base_url> <out.json> \
        --map laptop=computers-laptops \
        --map processor=computers-components \
        --limit 10

`--map src_path=category_slug` may be repeated. `src_path` is a path (with or
without a leading slash) under `base_url` that resolves to an OpenCart
category listing page; `category_slug` must be one of the slugs in
`catalog.management.commands.seed_store_catalog.TAXONOMY`.

Etiquette: one request per second (see tools/scrape/common.polite_get), a
real User-Agent identifying us, and --limit keeps each run to a handful of
pages -- these are partner stores who gave explicit permission to resell,
not scrape targets to hammer.
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # EcommerceInventory/

from catalog.scrape_parsers import parse_opencart_listing, parse_opencart_product  # noqa: E402
from tools.scrape.common import polite_get, write_fixture  # noqa: E402


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="e.g. https://potakait.com")
    parser.add_argument("out", help="output fixture JSON path")
    parser.add_argument(
        "--map",
        action="append",
        default=[],
        dest="maps",
        metavar="src_path=category_slug",
        required=True,
        help="listing path under base_url -> TAXONOMY category slug; repeatable",
    )
    parser.add_argument("--limit", type=int, default=10, help="max products per --map")
    return parser.parse_args(argv)


def _parse_maps(raw_maps):
    parsed = []
    for raw in raw_maps:
        if "=" not in raw:
            raise SystemExit(f"--map must be src_path=category_slug, got: {raw!r}")
        src_path, category_slug = raw.split("=", 1)
        parsed.append((src_path.strip().lstrip("/"), category_slug.strip()))
    return parsed


def scrape(base_url, maps, limit):
    base_url = base_url.rstrip("/") + "/"
    entries = []
    for src_path, category_slug in maps:
        listing_url = base_url + src_path
        print(f"[listing] {listing_url} -> {category_slug}")
        listing_html = polite_get(listing_url)
        product_urls = parse_opencart_listing(listing_html, listing_url)[:limit]
        print(f"  {len(product_urls)} product URL(s)")

        for url in product_urls:
            print(f"  [product] {url}")
            html = polite_get(url)
            p = parse_opencart_product(html)
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
                "source_url": url,  # partner stores only
            })
    return entries


def main(argv=None):
    args = parse_args(argv)
    maps = _parse_maps(args.maps)
    entries = scrape(args.base_url, maps, args.limit)
    write_fixture(args.out, entries)


if __name__ == "__main__":
    main()
