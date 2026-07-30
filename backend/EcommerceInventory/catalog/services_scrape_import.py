"""Admin browse/import from reference sites -- the machinery behind the two
admin-only endpoints in ``catalog.controllers.ProductImportController``.

Sources and their category mappings are DB-driven (``catalog.models.
ImportSource`` / ``ImportSourceCategory``), not a hardcoded dict -- the owner
manages them from the admin panel instead of needing a code change to add a
source or fix a category mapping. Three adapters exist in code: the OpenCart
one (potakait, canvasit), the Fabrilife one, and the Rokomari one (see the
0009 data migration -- a reference source, not a reseller partner, so
``sets_source_url=False``). A source with no working adapter
(``adapter_key=""``) must stay ``is_enabled=False`` -- enforced by
``ImportSource.clean()`` and re-checked here defensively.

Arogga is registered as a disabled ImportSource row (see the 0008 data
migration) carrying the reason in its `notes`: there is no parser for it and
it belongs to the separate medical/pharmacy phase (SP3).

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
from urllib.parse import quote

from django.utils.text import slugify

from catalog.models import ImportSource, Products
from catalog.scrape_parsers import (
    parse_fabrilife_listing,
    parse_fabrilife_product,
    parse_opencart_listing,
    parse_opencart_product,
    parse_rokomari_listing,
    parse_rokomari_product,
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

_ALGOLIA_APP_ID = "2UIXGXYA5O"
_ALGOLIA_SEARCH_KEY = "bfcfa7b10e2c9220df5d1d639d485218"  # public search-only key
_ALGOLIA_INDEX = "products"
_ALGOLIA_URL = f"https://{_ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/{_ALGOLIA_INDEX}/query"

# fabrilife's own facet category names -- this IS the live/authoritative
# mapping (lifted from tools/scrape/scrape_fabrilife.py, which already uses
# it to build fixtures), not a guess. Kept here as an adapter implementation
# detail (which Algolia facet string a given source_path maps to) rather
# than in the DB: ImportSourceCategory owns the admin-editable (path -> our
# taxonomy slug) mapping, this is the extra bit only the fabrilife adapter
# itself needs to talk to Algolia.
_FABRILIFE_CATS_BY_PATH = {
    "men-tshirts": ["Mens > Half Sleeve T-shirt", "Mens > Full Sleeve T-shirt"],
    "men-polos": ["Mens > Polo T-shirt"],
    "men-panjabi": ["Mens > Panjabi"],
    "men-hoodies": ["Mens > Hoodie", "Mens > Sweatshirt"],
    "women-kurti-tops": ["Womens > Kurti Tunic And Tops"],
    "women-tshirts": ["Womens > T-Shirt"],
    "kids-boys": ["Kids > Boys"],
    "kids-girls": ["Kids > Girls"],
}

FABRILIFE_BASE_URL = "https://fabrilife.com/"


class SourceFetchError(Exception):
    """A listing/search fetch failed outright (bad category, network error,
    site block) -- distinct from a single product failing, which is recorded
    per-item instead of raised."""


class UnsupportedSearchError(ValueError):
    """Raised when a free-text search (`q`) is requested for a source whose
    search isn't available (ImportSource.supports_search=False). A ValueError
    subclass so a caller that only distinguishes "bad input" from "network
    failure" still treats it as the former, but the view attaches it to the
    `q` field specifically rather than lumping it in with the generic
    "provide a category or search term" message."""


class DisabledSourceError(ValueError):
    """Raised when the requested ImportSource exists but is_enabled=False --
    e.g. arogga, which has no working adapter. A ValueError subclass so
    existing "bad input" handling in the view catches it, but the view
    attaches the source's own `notes` so the admin gets a real reason instead
    of a generic 400."""


def get_source_or_raise(slug):
    """Resolve a slug to its ImportSource row. Raises ValueError for an
    unknown slug (mirrors the old "Unknown or unsupported source" message)
    and DisabledSourceError for a real-but-disabled source -- callers that
    need to tell those two apart (the API must reject a disabled source with
    a clear message, not silently return nothing) can catch the more specific
    exception first."""
    source = ImportSource.objects.filter(slug=slug).first()
    if source is None:
        raise ValueError(f"Unknown or unsupported source: {slug!r}")
    if not source.is_enabled:
        reason = source.notes or "this source is currently disabled."
        raise DisabledSourceError(f"{source.name} is disabled -- {reason}")
    if not source.adapter_key:
        # Defensive: ImportSource.clean() already refuses to enable a source
        # with no adapter, but clean() only runs through ModelForm/full_clean
        # paths, not a bare .save() -- a management shell or a future admin
        # endpoint that skips it must not be able to make this function
        # attempt a fetch with no parser to run.
        raise DisabledSourceError(f"{source.name} has no adapter configured.")
    return source


def _source_categories(source):
    return [
        {"path": c.source_path, "label": c.label or c.source_path, "our_category": c.our_category_slug}
        for c in source.categories.all()
    ]


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
    base = source.base_url
    if category_path:
        return base + category_path.strip().lstrip("/")
    # Best-effort classic OpenCart search route. The exact scheme cannot be
    # verified against the live theme from this environment; a wrong scheme
    # degrades to "0 candidates" (parse_opencart_listing finds no cards),
    # not a crash, and an admin can always fall back to a category path.
    return base + f"index.php?route=product/search&search={query}&description=1"


def _rokomari_listing_url(source, category_path=None, query=None):
    """category_path is a full ``product/category/<id>/<slug>`` path (see
    ImportSourceCategory rows / the 0009 data migration); search hits the
    real ``/search?term=&search_type=ALL`` route -- verified live 2026-07-30,
    ``search_type=products`` (a plausible-looking guess) 500s, ``ALL`` (the
    value the site's own search form actually submits) works."""
    base = source.base_url
    if category_path:
        return base + category_path.strip().lstrip("/")
    return base + f"search?term={quote(query)}&search_type=ALL"


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


def browse_candidates(source_slug, *, category_path=None, query=None, limit=BROWSE_LIMIT, fetch=None):
    """Fetch a listing (or search) for the ImportSource identified by
    ``source_slug`` and return candidate products with enough detail to
    render a picker: name, price, discount_price, image URL(s), source URL,
    and whether we already have it (matched by slug).

    Also returns the category list for that source (from
    ``ImportSourceCategory``) so the caller can offer a dropdown instead of a
    free-text-only path. Raises ValueError for an unknown source,
    DisabledSourceError for a real-but-disabled source (e.g. arogga), and
    UnsupportedSearchError for a `query` against a source with
    supports_search=False (potakait.com).

    The response distinguishes two different reasons a browse can come back
    with zero candidates, since a silent empty state has bitten this codebase
    before: ``listing_product_count`` is how many product links the
    listing/search itself returned (0 genuinely means "nothing there"), and
    ``fetch_failures`` is how many of those individual product pages then
    failed to fetch/parse (a positive count with 0 candidates means "the
    source has products here but we couldn't read them" -- likely the site
    is down or blocking us -- not "empty category").
    """
    source = get_source_or_raise(source_slug)
    if not category_path and not query:
        raise ValueError("Provide a category or a search term.")
    if query and not source.supports_search:
        raise UnsupportedSearchError(
            f"{source.slug} search isn't available -- browse by category instead.")

    limit = max(1, min(int(limit or BROWSE_LIMIT), BROWSE_LIMIT))
    fetch = fetch or polite_get

    if source.adapter_key == "fabrilife":
        cats = _FABRILIFE_CATS_BY_PATH.get(category_path) if category_path else None
        try:
            listing_json = _fabrilife_search(cats=cats, query=query, hits_per_page=limit)
        except Exception as e:  # noqa: BLE001
            raise SourceFetchError(str(e)) from e
        product_urls = parse_fabrilife_listing(listing_json, source.base_url or FABRILIFE_BASE_URL)[:limit]
        parser = parse_fabrilife_product
    elif source.adapter_key == "rokomari":
        listing_url = _rokomari_listing_url(source, category_path, query)
        try:
            listing_html = fetch(listing_url)
        except Exception as e:  # noqa: BLE001 -- one bad listing must surface, not crash the process
            raise SourceFetchError(str(e)) from e
        product_urls = parse_rokomari_listing(listing_html, listing_url)[:limit]
        parser = parse_rokomari_product
    else:
        listing_url = _opencart_listing_url(source, category_path, query)
        try:
            listing_html = fetch(listing_url)
        except Exception as e:  # noqa: BLE001 -- one bad listing must surface, not crash the process
            raise SourceFetchError(str(e)) from e
        product_urls = parse_opencart_listing(listing_html, listing_url)[:limit]
        parser = parse_opencart_product

    categories = _source_categories(source)

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
    if source.sets_source_url:
        # Only partner stores (explicit reseller permission) get source_url --
        # that field marks products the price-sync re-prices. fabrilife is
        # not a partner and must never be enrolled.
        entry["source_url"] = url
    else:
        entry["gender"] = parsed.get("gender") or ""
        entry["sizes"] = parsed.get("sizes") or []
        entry["material"] = parsed.get("material") or ""
    return entry


def import_candidates(source_slug, source_urls, category, domain_user, added_by_user=None, *, fetch=None):
    """Fetch each of ``source_urls`` in turn, parse it, and create/skip a
    product+variant via ``catalog.services_import.seed_product_entry``.

    Capped at ``IMPORT_LIMIT`` -- the caller (the view) is expected to
    reject an over-cap request before calling this, but it is enforced here
    too so this function is safe to call directly.

    Returns a list of per-URL result dicts: ``{"source_url", "status"
    ("imported"|"skipped_exists"|"failed"), "reason", "product_id", "name"}``.
    A fetch/parse failure for one URL never aborts the rest of the batch.
    """
    source = get_source_or_raise(source_slug)
    fetch = fetch or polite_get
    if source.adapter_key == "fabrilife":
        parser = parse_fabrilife_product
    elif source.adapter_key == "rokomari":
        parser = parse_rokomari_product
    else:
        parser = parse_opencart_product

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
