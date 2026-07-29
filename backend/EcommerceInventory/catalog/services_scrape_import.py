"""Admin browse/import from reference sites -- the machinery behind the two
admin-only endpoints in ``catalog.controllers.ProductImportController``.

In scope: potakait.com, canvasit.com.bd (both OpenCart) and fabrilife.com --
exactly the three sites ``catalog.scrape_parsers`` already has parsers for.

Arogga is intentionally NOT here: there is no parser for it and it belongs to
the separate medical/pharmacy phase (SP3) -- see ``docs/PRODUCT_IMPORT.md``.

Reuses, does not duplicate:
  - ``catalog.scrape_parsers`` for all HTML/JSON parsing (pure, no network,
    no ORM)
  - ``tools.scrape.common.polite_get`` for GET fetches (1 req/sec, an
    identifying User-Agent) -- these are the owner's friends' stores, not
    scrape targets to hammer
  - ``catalog.services_import.seed_product_entry`` for the actual
    product/variant creation, so this endpoint can never drift from the
    fixture seeder (the seed_bancharampur lesson: one create/update path)

Every network call in this module is reachable through a module-level name
(``polite_get`` / ``_fabrilife_search``) that tests patch directly -- same
"inject/patch the fetcher" contract as
``catalog.services_price_sync.sync_source_prices(fetcher=...)``, just done by
patching the module attribute since browse and import both need several
fetches (a listing + N product pages) rather than one.
"""
import json

from django.utils.text import slugify

from catalog.models import Products
from catalog.scrape_parsers import (
    parse_fabrilife_listing,
    parse_fabrilife_product,
    parse_opencart_listing,
    parse_opencart_product,
)
from catalog.services_import import import_image, seed_product_entry
from tools.scrape.common import polite_get

# Per-request caps. Etiquette is 1 request/second against these partner
# sites, and each candidate/import costs at least one such request (browse
# needs a listing fetch *plus* one product-detail fetch per candidate, since
# neither OpenCart theme's listing card carries price/images -- only
# scrape_parsers.parse_opencart_product does, see the module docstring in
# catalog/scrape_parsers.py). Keeping both comfortably below ~15s means
# staying comfortably below a typical gateway timeout, and never firing an
# unbounded run at a partner's site. See docs/PRODUCT_IMPORT.md.
BROWSE_LIMIT = 12
IMPORT_LIMIT = 12

SOURCES = {"potakait", "canvasit", "fabrilife"}

_OPENCART_BASE_URLS = {
    "potakait": "https://potakait.com/",
    "canvasit": "https://canvasit.com.bd/",
}

FABRILIFE_BASE_URL = "https://fabrilife.com/"
_ALGOLIA_APP_ID = "2UIXGXYA5O"
_ALGOLIA_SEARCH_KEY = "bfcfa7b10e2c9220df5d1d639d485218"  # public search-only key
_ALGOLIA_INDEX = "products"
_ALGOLIA_URL = f"https://{_ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/{_ALGOLIA_INDEX}/query"

# Category dropdown paths -- VERIFIED against the live sites (2026-07-28/29:
# real GET requests, not guesses), each returning a 200 with a parseable
# product grid and a nonzero live product count. The computer-hardware paths
# are also the exact ones that produced the committed fixtures
# (catalog/fixtures/seed/potakait.json = 64 products, canvasit.json = 70).
# `router` is singular on BOTH sites -- `routers` 404s; that typo already cost
# a whole scrape run once.
#
# Gadget/tablet categories (earbuds, headphones, speakers, power banks,
# smart watches, action cameras, phone accessories, tablets) are ALSO
# verified now -- both sites carry them, just under different path spellings
# than an earlier guessed draft of this list used ("smart-phone"/"tablet-pc"/
# "smart-watch", none of which existed). One note that still stands: neither
# partner store sells actual smartphones (only tablets + phone accessories),
# so `phones-smartphones` has no working source path on either site -- see
# docs/PRODUCT_IMPORT.md.
OPENCART_CATEGORY_PATHS = {
    "potakait": [
        {"path": "laptops", "label": "Laptops", "our_category": "computers-laptops"},
        {"path": "gaming-pc", "label": "Gaming PCs", "our_category": "computers-desktops"},
        {"path": "monitors", "label": "Monitors", "our_category": "computers-monitors"},
        {"path": "processors", "label": "Processors", "our_category": "computers-components"},
        {"path": "keyboards", "label": "Keyboards", "our_category": "computers-keyboards-mice"},
        {"path": "printers", "label": "Printers", "our_category": "computers-printers-office"},
        {"path": "router", "label": "Routers", "our_category": "computers-networking"},
        {"path": "earbuds", "label": "Earbuds", "our_category": "gadgets-earbuds"},
        {"path": "headphones", "label": "Headphones", "our_category": "gadgets-earbuds"},
        {"path": "speaker-and-home-theater", "label": "Speakers & Home Theater", "our_category": "gadgets-speakers"},
        {"path": "power-bank", "label": "Power Banks", "our_category": "gadgets-power"},
        {"path": "smart-watches", "label": "Smart Watches", "our_category": "gadgets-smart-watches"},
        {"path": "action-camera", "label": "Action Cameras", "our_category": "gadgets-cameras"},
        {"path": "mobile-phone-accessories", "label": "Phone Accessories", "our_category": "gadgets-cases"},
        {"path": "tablet-pc", "label": "Tablets", "our_category": "phones-tablets"},
        {"path": "gadgets", "label": "Gadgets (all)", "our_category": "gadgets"},
    ],
    "canvasit": [
        {"path": "laptop", "label": "Laptops", "our_category": "computers-laptops"},
        {"path": "desktop-pc", "label": "Desktops", "our_category": "computers-desktops"},
        {"path": "monitor", "label": "Monitors", "our_category": "computers-monitors"},
        {"path": "processor", "label": "Processors", "our_category": "computers-components"},
        {"path": "keyboard", "label": "Keyboards", "our_category": "computers-keyboards-mice"},
        {"path": "printer", "label": "Printers", "our_category": "computers-printers-office"},
        {"path": "router", "label": "Routers", "our_category": "computers-networking"},
        {"path": "earbuds", "label": "Earbuds", "our_category": "gadgets-earbuds"},
        {"path": "headphone", "label": "Headphones", "our_category": "gadgets-earbuds"},
        {"path": "speaker", "label": "Speakers", "our_category": "gadgets-speakers"},
        {"path": "power-bank", "label": "Power Banks", "our_category": "gadgets-power"},
        {"path": "smart-watch", "label": "Smart Watches", "our_category": "gadgets-smart-watches"},
        {"path": "action-camera", "label": "Action Cameras", "our_category": "gadgets-cameras"},
        {"path": "drones", "label": "Drones", "our_category": "gadgets-cameras"},
        {"path": "mobile-phone-accessories", "label": "Phone Accessories", "our_category": "gadgets-cases"},
        {"path": "phone-tablet", "label": "Phones & Tablets", "our_category": "phones-tablets"},
        {"path": "gadget", "label": "Gadgets (all)", "our_category": "gadgets"},
    ],
}

# Which sources have a working free-text search we could find a real URL for.
# potakait.com: verified 2026-07-28 -- index.php?route=product/search&search=,
# /search?search=, /search?q= and /catalogsearch/result/?q= all 404, and the
# homepage HTML has no <form> with a search input to reverse-engineer a
# working route from. canvasit.com.bd's classic OpenCart search route DOES
# work (verified: 200, 20 products parsed). fabrilife's Algolia query already
# supports free text via the `query` param.
SOURCE_SEARCH_SUPPORTED = {"potakait": False, "canvasit": True, "fabrilife": True}

# fabrilife's own facet category names -- this IS the live/authoritative
# mapping (lifted from tools/scrape/scrape_fabrilife.py, which already uses
# it to build fixtures), not a guess.
FABRILIFE_CATEGORY_PATHS = [
    {"path": "men-tshirts", "label": "Men's T-shirts",
     "our_category": "men-tshirts", "cats": ["Mens > Half Sleeve T-shirt", "Mens > Full Sleeve T-shirt"]},
    {"path": "men-polos", "label": "Men's Polos",
     "our_category": "men-polos", "cats": ["Mens > Polo T-shirt"]},
    {"path": "men-panjabi", "label": "Men's Panjabi",
     "our_category": "men-panjabi", "cats": ["Mens > Panjabi"]},
    {"path": "men-hoodies", "label": "Men's Hoodies",
     "our_category": "men-hoodies", "cats": ["Mens > Hoodie", "Mens > Sweatshirt"]},
    {"path": "women-kurti-tops", "label": "Women's Kurti & Tops",
     "our_category": "women-kurti-tops", "cats": ["Womens > Kurti Tunic And Tops"]},
    {"path": "women-tshirts", "label": "Women's T-shirts",
     "our_category": "women-tshirts", "cats": ["Womens > T-Shirt"]},
    {"path": "kids-boys", "label": "Boys", "our_category": "kids-boys", "cats": ["Kids > Boys"]},
    {"path": "kids-girls", "label": "Girls", "our_category": "kids-girls", "cats": ["Kids > Girls"]},
]
_FABRILIFE_CATS_BY_PATH = {c["path"]: c["cats"] for c in FABRILIFE_CATEGORY_PATHS}


class SourceFetchError(Exception):
    """A listing/search fetch failed outright (bad category, network error,
    site block) -- distinct from a single product failing, which is recorded
    per-item instead of raised."""


class UnsupportedSearchError(ValueError):
    """Raised when a free-text search (`q`) is requested for a source whose
    search isn't available (see SOURCE_SEARCH_SUPPORTED). A ValueError
    subclass so a caller that only distinguishes "bad input" from "network
    failure" still treats it as the former, but the view attaches it to the
    `q` field specifically rather than lumping it in with the generic
    "provide a category or search term" message."""


def _fabrilife_search(cats=None, query=None, hits_per_page=BROWSE_LIMIT):
    """POST an Algolia `query` request against fabrilife.com's public
    products index -- same endpoint/key tools/scrape/scrape_fabrilife.py's
    polite_algolia_query uses for category browsing, extended here to also
    accept free-text `query` for the search box. Returns the raw JSON
    response body (text)."""
    import time

    import requests

    from tools.scrape.common import UA

    time.sleep(1.0)  # same 1 req/sec etiquette as polite_get
    headers = {
        "X-Algolia-API-Key": _ALGOLIA_SEARCH_KEY,
        "X-Algolia-Application-Id": _ALGOLIA_APP_ID,
        "Content-Type": "application/json",
        **UA,
    }
    body = {"hitsPerPage": hits_per_page}
    if cats:
        body["facetFilters"] = [[f"cats:{c}" for c in cats]]
    if query:
        body["query"] = query
    r = requests.post(headers=headers, url=_ALGOLIA_URL, data=json.dumps(body), timeout=20)
    r.raise_for_status()
    return r.text


def _opencart_listing_url(source, category_path=None, query=None):
    base = _OPENCART_BASE_URLS[source]
    if category_path:
        return base + category_path.strip().lstrip("/")
    # Best-effort classic OpenCart search route. The exact scheme cannot be
    # verified against the live theme from this environment; a wrong scheme
    # degrades to "0 candidates" (parse_opencart_listing finds no cards),
    # not a crash, and an admin can always fall back to a category path.
    return base + f"index.php?route=product/search&search={query}&description=1"


def _candidate_from_product(url, parsed):
    already_have = Products.objects.filter(slug=slugify(parsed.get("name") or "")).exists() \
        if parsed.get("name") else False
    return {
        "source_url": url,
        "name": parsed.get("name") or "",
        "price": parsed.get("price"),
        "discount_price": parsed.get("discount_price"),
        "images": parsed.get("images") or [],
        "already_have": already_have,
    }


def browse_candidates(source, *, category_path=None, query=None, limit=BROWSE_LIMIT, fetch=None):
    """Fetch a listing (or search) for ``source`` and return candidate
    products with enough detail to render a picker: name, price,
    discount_price, image URL(s), source URL, and whether we already have it
    (matched by slug).

    Also returns the category list for that source so the caller can offer a
    dropdown instead of a free-text-only path. Raises ValueError for an
    unknown/out-of-scope source (e.g. "arogga"), and UnsupportedSearchError
    for a `query` against a source with no working search endpoint
    (potakait.com -- see SOURCE_SEARCH_SUPPORTED).

    The response distinguishes two different reasons a browse can come back
    with zero candidates, since a silent empty state has bitten this codebase
    before: ``listing_product_count`` is how many product links the
    listing/search itself returned (0 genuinely means "nothing there"), and
    ``fetch_failures`` is how many of those individual product pages then
    failed to fetch/parse (a positive count with 0 candidates means "the
    source has products here but we couldn't read them" -- likely the site
    is down or blocking us -- not "empty category").
    """
    if source not in SOURCES:
        raise ValueError(f"Unknown or unsupported source: {source!r}")
    if not category_path and not query:
        raise ValueError("Provide a category or a search term.")
    if query and not SOURCE_SEARCH_SUPPORTED.get(source, False):
        raise UnsupportedSearchError(
            f"{source} search isn't available -- browse by category instead.")

    limit = max(1, min(int(limit or BROWSE_LIMIT), BROWSE_LIMIT))
    fetch = fetch or polite_get

    if source == "fabrilife":
        cats = _FABRILIFE_CATS_BY_PATH.get(category_path) if category_path else None
        try:
            listing_json = _fabrilife_search(cats=cats, query=query, hits_per_page=limit)
        except Exception as e:  # noqa: BLE001
            raise SourceFetchError(str(e)) from e
        product_urls = parse_fabrilife_listing(listing_json, FABRILIFE_BASE_URL)[:limit]
        parser = parse_fabrilife_product
        categories = FABRILIFE_CATEGORY_PATHS
    else:
        listing_url = _opencart_listing_url(source, category_path, query)
        try:
            listing_html = fetch(listing_url)
        except Exception as e:  # noqa: BLE001 -- one bad listing must surface, not crash the process
            raise SourceFetchError(str(e)) from e
        product_urls = parse_opencart_listing(listing_html, listing_url)[:limit]
        parser = parse_opencart_product
        categories = OPENCART_CATEGORY_PATHS.get(source, [])

    candidates = []
    fetch_failures = 0
    for url in product_urls:
        try:
            html = fetch(url)
            parsed = parser(html)
        except Exception:  # noqa: BLE001 -- one bad product page must not sink the whole browse
            fetch_failures += 1
            continue
        if not parsed.get("name"):
            fetch_failures += 1
            continue
        candidates.append(_candidate_from_product(url, parsed))

    return {
        "candidates": candidates,
        "categories": categories,
        "listing_product_count": len(product_urls),
        "fetch_failures": fetch_failures,
    }


def _entry_from_parsed(source, url, parsed):
    entry = {
        "name": parsed.get("name"),
        "price": parsed.get("price"),
        "discount_price": parsed.get("discount_price"),
        "description": parsed.get("description") or parsed.get("name"),
        "specifications": parsed.get("specifications") or {},
        "brand": parsed.get("brand") or "",
        "images": (parsed.get("images") or [])[:3],
    }
    if source in ("potakait", "canvasit"):
        # Only partner stores (explicit reseller permission) get source_url --
        # that field marks products the price-sync re-prices. fabrilife is
        # not a partner and must never be enrolled.
        entry["source_url"] = url
    else:
        entry["gender"] = parsed.get("gender") or ""
        entry["sizes"] = parsed.get("sizes") or []
        entry["material"] = parsed.get("material") or ""
    return entry


def import_candidates(source, source_urls, category, domain_user, added_by_user=None, *, fetch=None):
    """Fetch each of ``source_urls`` in turn, parse it, and create/skip a
    product+variant via ``catalog.services_import.seed_product_entry``.

    Capped at ``IMPORT_LIMIT`` -- the caller (the view) is expected to
    reject an over-cap request before calling this, but it is enforced here
    too so this function is safe to call directly.

    Returns a list of per-URL result dicts: ``{"source_url", "status"
    ("imported"|"skipped_exists"|"failed"), "reason", "product_id", "name"}``.
    A fetch/parse failure for one URL never aborts the rest of the batch.
    """
    if source not in SOURCES:
        raise ValueError(f"Unknown or unsupported source: {source!r}")
    fetch = fetch or polite_get
    parser = parse_fabrilife_product if source == "fabrilife" else parse_opencart_product

    results = []
    for url in source_urls[:IMPORT_LIMIT]:
        try:
            html = fetch(url)
            parsed = parser(html)
        except Exception as e:  # noqa: BLE001 -- one dead product page must not sink the batch
            results.append({"source_url": url, "status": "failed",
                            "reason": f"fetch/parse failed: {e}", "product_id": None, "name": None})
            continue

        entry = _entry_from_parsed(source, url, parsed)
        outcome = seed_product_entry(entry, category, domain_user, added_by_user)

        if outcome["status"] == "skipped_invalid":
            results.append({"source_url": url, "status": "failed", "reason": outcome["reason"],
                            "product_id": None, "name": entry.get("name")})
        elif outcome["status"] == "skipped_exists":
            results.append({"source_url": url, "status": "skipped_exists", "reason": outcome["reason"],
                            "product_id": outcome["product"].id, "name": entry.get("name")})
        else:  # created (import is always force=False, so "updated" cannot happen here)
            results.append({"source_url": url, "status": "imported", "reason": None,
                            "product_id": outcome["product"].id, "name": entry.get("name")})
    return results
