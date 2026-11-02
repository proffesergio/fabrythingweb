"""HTML parsers shared by the offline scrape scripts (tools/scrape/) and the
runtime price-sync service. Pure functions: str in, plain data out -- no
network, no ORM, so they are unit-testable against saved page snippets.

Written against the OpenCart theme actually served by potakait.com (verified
2026-07-28 against a live product page), not against generic OpenCart
assumptions:

- Title: ``h1.product_title``
- Current/discount price: ``div.price-wrapper`` holding ``span.special``
  (always present -- the price you actually pay) and, only when the item is
  discounted, a second ``span.price`` (the crossed-out original price).
- Brand: a ``div.product-wid-info`` row whose first ``<p>`` reads "Brand"
  (colon/space padding present in the wild), with the brand name in a
  sibling ``<a>``.
- Images: ``img`` tags inside ``#gallery`` (thumbnails + the main preview,
  which duplicates the first thumbnail -- deduped away).
- Specifications: ``table.data-table`` rows of ``td.name`` / ``td.value``
  pairs; section header rows (``td.heading-row``, colspan=3) carry no value
  cell and are skipped.
- Description: the free-text block in ``#description .descriptionContent``.

canvasit.com.bd is the same OpenCart *family* but a different theme (verified
2026-07-28 against https://canvasit.com.bd/laptop and a live product page)
with incompatible markup for everything except the outer product link:

- Listing cards: ``.product-layout`` wrapping ``.product-thumb`` (potakait's
  theme uses ``.product-item`` instead) -- both selectors are tried and
  deduped, since a ``.product-layout`` and the ``.product-thumb`` it wraps
  resolve to the same product URL.
- Title: a plain ``<h1>`` inside ``.title.page-title`` (no ``product_title``
  class).
- Current/discount price: ``div.price-wrapper > .price-group`` holding
  ``.product-price-new`` (current price) and, only when discounted,
  ``.product-price-old`` (crossed-out original) -- distinct class names from
  potakait's ``.special``/``.price``, and the presence of ``.price-group`` is
  what ``_detect_opencart_theme`` keys off of.
- Brand: ``li.product-manufacturer a``.
- Images: ``img`` tags inside ``.product-image .swiper-slide`` (the main
  image carousel); there is no ``#gallery`` on this theme.
- Specifications: ``.block-attributes table.table-bordered`` rows of two
  plain ``<td>`` cells; section header rows are a single
  ``<td colspan="2">`` and are skipped.
- Description: ``.block-content.block-description`` (the "Description" tab
  panel; the tab's own ``id`` is a random per-page hash so it can't be
  selected directly).

The two themes diverge enough in price/specs/description markup that each
gets its own small extractor (``_extract_*_potakait`` / ``_extract_*_canvasit``)
rather than one function full of ``or`` fallbacks.
"""
import json
import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

_PRICE_RE = re.compile(r"[\d,]+(?:\.\d+)?")
# rokomari.com formats prices "TK. 554" / "TK.554" (no ৳ symbol at all) --
# stripped explicitly here (rather than relying on _PRICE_RE to just skip
# over the letters) so the intent is legible and future price-string tweaks
# on either site can't accidentally break the other's parsing.
_TK_PREFIX_RE = re.compile(r"tk\.?", re.IGNORECASE)
# rokomari.com listing cards render brand as "Brand: X" (see
# parse_rokomari_listing_cards) -- stripped so the affiliate picker gets a
# bare brand name, same shape as every other adapter's `brand` field.
_ROKOMARI_LISTING_BRAND_PREFIX_RE = re.compile(r"^brand:\s*", re.IGNORECASE)


def parse_bdt_price(text):
    """Parse a BDT price string like ``"8,500৳"``, ``"৳ 12,990"`` or
    rokomari.com's ``"TK. 554"`` into a float. Returns ``None`` when the text
    has no digits (e.g. "Out of stock")."""
    if not text:
        return None
    cleaned = _TK_PREFIX_RE.sub("", text.replace("৳", "")).strip()  # strip Taka sign / TK. prefix
    m = _PRICE_RE.search(cleaned)
    if not m or not any(c.isdigit() for c in m.group()):
        return None
    try:
        return float(m.group().replace(",", ""))
    except ValueError:
        return None


def _strip_query(url):
    parts = urlsplit(url)
    return parts._replace(query="", fragment="").geturl()


def _dedupe_preserve_order(items):
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _extract_brand_potakait(soup):
    for row in soup.select(".product-wid-info"):
        label = row.find("p")
        if label and "brand" in label.get_text(strip=True).lower():
            link = row.find("a")
            if link:
                return link.get_text(strip=True)
    return ""


def _extract_brand_canvasit(soup):
    link = soup.select_one(".product-manufacturer a")
    return link.get_text(strip=True) if link else ""


def _extract_prices_potakait(soup):
    wrap = soup.select_one(".price-wrapper")
    if wrap is None:
        return None, None
    special = wrap.select_one(".special")
    old = wrap.select_one(".price")
    special_val = parse_bdt_price(special.get_text()) if special else None
    old_val = parse_bdt_price(old.get_text()) if old else None
    if special_val is not None and old_val is not None:
        # Discounted: .special is the lower, current price; .price is the
        # crossed-out original.
        return old_val, special_val
    if special_val is not None:
        return special_val, None
    return old_val, None


def _extract_prices_canvasit(soup):
    group = soup.select_one(".price-wrapper .price-group")
    if group is None:
        return None, None
    new = group.select_one(".product-price-new")
    old = group.select_one(".product-price-old")
    new_val = parse_bdt_price(new.get_text()) if new else None
    old_val = parse_bdt_price(old.get_text()) if old else None
    if old_val is not None and new_val is not None:
        # Discounted: .product-price-new is the lower, current price;
        # .product-price-old is the crossed-out original.
        return old_val, new_val
    if new_val is not None:
        return new_val, None
    return old_val, None


def _extract_images_potakait(soup, base_url):
    gallery = soup.select_one("#gallery")
    if gallery is None:
        return []
    urls = []
    for img in gallery.find_all("img"):
        src = img.get("src")
        if not src:
            continue
        urls.append(_strip_query(urljoin(base_url, src)))
    return _dedupe_preserve_order(urls)


def _extract_images_canvasit(soup, base_url):
    urls = []
    for img in soup.select(".product-image .swiper-slide img"):
        src = img.get("src")
        if not src:
            continue
        urls.append(_strip_query(urljoin(base_url, src)))
    return _dedupe_preserve_order(urls)


def _extract_specifications_potakait(soup):
    specs = {}
    for row in soup.select("table.data-table tr"):
        name = row.find("td", class_="name")
        value = row.find("td", class_="value")
        if name and value:
            specs[name.get_text(strip=True)] = value.get_text(strip=True)
    return specs


def _extract_specifications_canvasit(soup):
    specs = {}
    for row in soup.select(".block-attributes table.table-bordered tr"):
        tds = row.find_all("td")
        # Section header rows are a single <td colspan="2"> and carry no
        # value cell; regular rows are exactly two plain <td>s.
        if len(tds) != 2 or tds[0].get("colspan"):
            continue
        name = tds[0].get_text(strip=True)
        if not name:
            continue
        specs[name] = tds[1].get_text(separator=" ", strip=True)
    return specs


def _extract_description_potakait(soup):
    node = soup.select_one("#description .descriptionContent") or soup.select_one("#description")
    if node is None:
        return ""
    return node.get_text(separator="\n", strip=True)


def _extract_description_canvasit(soup):
    node = soup.select_one(".block-content.block-description")
    if node is None:
        return ""
    return node.get_text(separator="\n", strip=True)


def _detect_opencart_theme(soup):
    """potakait.com and canvasit.com.bd are both OpenCart but run different
    themes with incompatible price/specs/description markup. Detect once up
    front -- canvasit nests its price in a ``.price-group``, potakait
    doesn't -- and dispatch to theme-specific extractors below rather than
    scattering ``or`` fallbacks through every field."""
    if soup.select_one(".price-wrapper .price-group") is not None:
        return "canvasit"
    return "potakait"


def parse_opencart_product(html):
    """Parse a single OpenCart product page into a plain dict with keys:
    name, price, discount_price, description, specifications, brand, images
    (absolute URLs).

    Handles both partner themes (potakait.com and canvasit.com.bd -- see the
    module docstring for the markup each uses). The base URL for resolving
    image ``src`` attributes is read from the page's own ``<base href>`` tag
    -- present on both themes -- so callers only need to pass the page
    HTML."""
    soup = BeautifulSoup(html, "html.parser")

    base_tag = soup.find("base", href=True)
    base_url = base_tag["href"] if base_tag else ""

    theme = _detect_opencart_theme(soup)

    h1 = soup.select_one("h1.product_title") or soup.select_one(".page-title h1") or soup.find("h1")
    name = h1.get_text(strip=True) if h1 else ""

    if theme == "canvasit":
        price, discount_price = _extract_prices_canvasit(soup)
        brand = _extract_brand_canvasit(soup)
        images = _extract_images_canvasit(soup, base_url)
        specifications = _extract_specifications_canvasit(soup)
        description = _extract_description_canvasit(soup)
    else:
        price, discount_price = _extract_prices_potakait(soup)
        brand = _extract_brand_potakait(soup)
        images = _extract_images_potakait(soup, base_url)
        specifications = _extract_specifications_potakait(soup)
        description = _extract_description_potakait(soup)

    return {
        "name": name,
        "price": price,
        "discount_price": discount_price,
        "description": description,
        "specifications": specifications,
        "brand": brand,
        "images": images,
    }


def parse_opencart_listing(html, base_url):
    """Parse an OpenCart category listing page into a list of absolute
    product page URLs (deduped, order preserved).

    potakait's theme wraps each card in ``.product-item``; canvasit's wraps
    it in ``.product-layout`` containing a ``.product-thumb``. All three
    selectors are tried; a ``.product-layout`` and the ``.product-thumb`` it
    contains resolve to the same product URL (both find the same first
    ``<a href>``), so the dedupe below collapses them to one entry."""
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    for card in soup.select(".product-item, .product-thumb, .product-layout"):
        link = card.find("a", href=True)
        if link:
            urls.append(urljoin(base_url, link["href"]))
    return _dedupe_preserve_order(urls)


# ---------------------------------------------------------------------------
# Fabrilife (fabrilife.com) -- one-time seed source, NOT a resale partner.
#
# Verified 2026-07-28 against live product pages (e.g.
# https://fabrilife.com/product/72899-premium-jacquard-panjabi-sabri). The
# product *detail* page is plain server-rendered HTML, no JS shell:
#
# - Title: the ``h4.tiny-margin`` inside ``.product-title-row`` (there are
#   other ``.tiny-margin`` headings on the page -- "Frequently Bought
#   Together", "You may also like" -- but those are ``h5``, not ``h4``).
# - Price: ``.price-now .price_field`` is always present (the price you pay).
#   ``.price-old .regular_price_field`` only appears when the item is
#   discounted, and holds the crossed-out original price.
# - Sizes: one ``div.size-selector`` per offered size; its text is the size
#   label ("44", "M", "10/11Y" -- format varies by product type).
# - Images: ``img.product-image`` inside ``.product-image-container`` (the
#   visible slide plus the hidden alternates the JS swaps in on thumbnail
#   click). No ``<base href>`` tag on this theme, so the origin is read from
#   the page's own ``<meta property="og:url">`` tag instead.
# - Gender + material: not in the visible DOM as clean fields. Every product
#   page embeds a GA4 tracking object (``var g4a = {...};``) with
#   ``item_category`` ("Mens"/"Womens"/"Kids"/"Teens") -- reused here rather
#   than guessing gender from the title. Material is free text inside
#   ``.self-product-description``; when a "Fabric Type:" (or "Fabric:"/
#   "Material:") label is present, the value immediately after it is used,
#   trimmed at the first marketing dash (" - " / " -- "); when the product's
#   description doesn't state it in that form, material is "" rather than
#   guessed.
#
# Listing: the brief's assumed faceted URL
# (``/shop?refinementList[cats][0]=...``) renders its result grid with
# Algolia InstantSearch client-side JS -- the raw HTML response for that URL
# contains zero product links in the actual results grid (only unrelated
# "New Arrivals" mega-menu links, confirmed by fetching it directly). The
# page's own JS talks to Algolia directly with a public
# **search-only** API key embedded in the page source
# (``algoliasearch('2UIXGXYA5O', ...)``, index ``products``) -- the same
# mechanism the site itself uses for `/shop`, so ``parse_fabrilife_listing``
# consumes *that* JSON response body (not HTML) and is named/typed to match
# the OpenCart listing parser regardless.
# ---------------------------------------------------------------------------

_GENDER_RE = re.compile(r'"item_category"\s*:\s*"([^"]+)"')
_BRAND_RE = re.compile(r'"item_brand"\s*:\s*"([^"]+)"')
_GENDER_MAP = {
    "mens": "MEN",
    "womens": "WOMEN",
    "women": "WOMEN",
    "kids": "KIDS",
    "teens": "KIDS",
}
_MATERIAL_LABELS = {"fabric type", "fabric", "material"}
_DASH_SPLIT_RE = re.compile(r"\s[–—-]\s")  # " - ", " -- ", " -- "

# fabrilife.com's own public, search-only Algolia key (read straight from the
# page's own JS: ``algoliasearch('2UIXGXYA5O', ...)``). Kept here rather than
# in tools/scrape/scrape_fabrilife.py (which reads these back from this
# module) so the runtime size-chart backfill command
# (catalog.services_size_chart_backfill) and the offline one-time scraper
# can't drift onto two different keys/index names.
FABRILIFE_ALGOLIA_APP_ID = "2UIXGXYA5O"
FABRILIFE_ALGOLIA_SEARCH_KEY = "bfcfa7b10e2c9220df5d1d639d485218"
FABRILIFE_ALGOLIA_INDEX = "products"
FABRILIFE_ALGOLIA_URL = (
    f"https://{FABRILIFE_ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/{FABRILIFE_ALGOLIA_INDEX}/query"
)


def _fabrilife_base_url(soup):
    tag = soup.find("meta", attrs={"property": "og:url"})
    if tag and tag.get("content"):
        parts = urlsplit(tag["content"])
        if parts.scheme and parts.netloc:
            return f"{parts.scheme}://{parts.netloc}/"
    return "https://fabrilife.com/"


def _extract_fabrilife_gender(html):
    m = _GENDER_RE.search(html)
    if not m:
        return ""
    return _GENDER_MAP.get(m.group(1).strip().lower(), "")


def _extract_fabrilife_brand(html):
    m = _BRAND_RE.search(html)
    return m.group(1).strip() if m else "Fabrilife"


def _extract_fabrilife_prices(soup):
    now = soup.select_one(".price-now .price_field")
    old = soup.select_one(".price-old .regular_price_field")
    now_val = parse_bdt_price(now.get_text()) if now else None
    old_val = parse_bdt_price(old.get_text()) if old else None
    if old_val is not None and now_val is not None:
        # .price-old is the crossed-out original; .price-now is what you pay.
        return old_val, now_val
    return now_val, None


def _extract_fabrilife_sizes(soup):
    return [el.get_text(strip=True) for el in soup.select(".size-selector") if el.get_text(strip=True)]


_HEADER_PAREN_RE = re.compile(r"\s*\([^)]*\)")


def _slugify_size_chart_header(text):
    """"Chest (round)" -> "chest", "Length" -> "length". Drops a parenthetical
    qualifier rather than keeping it in the key, matching the plain
    ``{"chest": 36, "length": 27}`` shape documented on
    ``catalog.models.Products.size_chart``."""
    return _HEADER_PAREN_RE.sub("", text).strip().lower().replace(" ", "_")


def _extract_fabrilife_size_chart(soup):
    """Parse the "Size chart - In inches (...)" table into
    ``{"M": {"chest": 36.0, "length": 30.0, "sleeve": 21.0}, ...}``.

    Only the INCH tab-pane (``id`` starting ``sizechart-inch``) is read --
    the site also pre-renders a CM table (``sizechart-cm-*``) with the same
    values times 2.54, but that is a second, separately-maintained source
    that could in principle drift out of sync with the INCH one. The
    storefront instead derives CM from these INCH values at render time, so
    the CM table on the source page is deliberately ignored here.

    Returns ``{}`` when the page has no size chart at all (most Fabrilife
    products besides Tops/Kurti don't carry measurements)."""
    table = None
    for pane in soup.select(".tab-pane"):
        pane_id = pane.get("id") or ""
        if pane_id.startswith("sizechart-inch"):
            table = pane.find("table")
            break
    if table is None:
        return {}

    header_cells = table.select("thead th")
    if len(header_cells) < 2:
        return {}
    size_label, *measurement_labels = [th.get_text(strip=True) for th in header_cells]
    if size_label.lower() != "size":
        return {}
    measurement_keys = [_slugify_size_chart_header(h) for h in measurement_labels]

    chart = {}
    for row in table.select("tbody tr"):
        cells = row.find_all("td")
        if not cells:
            continue
        size = cells[0].get_text(strip=True)
        if not size:
            continue
        measurements = {}
        for key, cell in zip(measurement_keys, cells[1:]):
            value = parse_bdt_price(cell.get_text(strip=True))
            if value is not None:
                measurements[key] = value
        if measurements:
            chart[size] = measurements
    return chart


def _extract_fabrilife_images(soup, base_url):
    urls = []
    for img in soup.select(".product-image-container img.product-image"):
        src = img.get("src")
        if not src:
            continue
        urls.append(_strip_query(urljoin(base_url, src)))
    return _dedupe_preserve_order(urls)


def _fabrilife_description_node(soup):
    return soup.select_one(".self-product-description")


def _extract_fabrilife_description(desc_node):
    if desc_node is None:
        return ""
    return desc_node.get_text(separator=" ", strip=True)


def _extract_fabrilife_specs_and_material(desc_node):
    """Walk every ``<strong>``/``<b>`` label inside the description block and
    pair it with the text immediately following it, up to the next label or
    a ``<br>``. Labels with no following text (e.g. a lone "Product
    Specification:" heading) are skipped rather than stored as empty."""
    specs = {}
    material = ""
    if desc_node is None:
        return specs, material

    for label_tag in desc_node.select("strong, b"):
        label = label_tag.get_text(strip=True).rstrip(":").strip()
        if not label:
            continue
        value_parts = []
        for sib in label_tag.next_siblings:
            name = getattr(sib, "name", None)
            if name in ("br",) or (name in ("strong", "b")):
                break
            text = sib if isinstance(sib, str) else sib.get_text()
            value_parts.append(text)
        value = "".join(value_parts).strip()
        value = value.lstrip("✔️").strip()  # leading checkmark bullets
        if not value:
            continue
        specs[label] = value
        if not material and label.lower() in _MATERIAL_LABELS:
            material = _DASH_SPLIT_RE.split(value, maxsplit=1)[0].strip()

    return specs, material


def parse_fabrilife_product(html):
    """Parse a single Fabrilife product page into a plain dict with the same
    keys as ``parse_opencart_product`` (name, price, discount_price,
    description, specifications, brand, images) plus ``gender``
    (``"MEN"``/``"WOMEN"``/``"KIDS"``), ``sizes`` (list), ``material``
    (``""`` when the description doesn't state it) and ``size_chart``
    (``{}`` when the page has none -- see ``_extract_fabrilife_size_chart``)."""
    soup = BeautifulSoup(html, "html.parser")
    base_url = _fabrilife_base_url(soup)

    title_el = soup.select_one(".product-title-row h4.tiny-margin") or soup.select_one("h4.tiny-margin")
    name = title_el.get_text(strip=True) if title_el else ""

    price, discount_price = _extract_fabrilife_prices(soup)
    desc_node = _fabrilife_description_node(soup)
    specifications, material = _extract_fabrilife_specs_and_material(desc_node)

    return {
        "name": name,
        "price": price,
        "discount_price": discount_price,
        "description": _extract_fabrilife_description(desc_node),
        "specifications": specifications,
        "brand": _extract_fabrilife_brand(html),
        "images": _extract_fabrilife_images(soup, base_url),
        "gender": _extract_fabrilife_gender(html),
        "sizes": _extract_fabrilife_sizes(soup),
        "material": material,
        "size_chart": _extract_fabrilife_size_chart(soup),
    }


def parse_fabrilife_algolia_size_chart(raw):
    """Parse the ``size_chart`` field of a fabrilife.com Algolia ``products``
    search hit into the same shape ``_extract_fabrilife_size_chart`` produces
    from the live page's HTML table: ``{"M": {"chest": 36.0, "length": 30.0,
    "sleeve": 21.0}, ...}``.

    Confirmed live (2026-07-29) against a query for "Womens Premium Tops -
    Estrella": the hit itself carries a ``size_chart`` field, a JSON-encoded
    *string* shaped like
    ``[{"title": "...", "unit_of_measurement": "inch", "chart": {"M":
    {"chest (round)": "36", "length": "30", "sleeve": "21"}, ...}}]`` --
    fabrilife.com's own structured data behind the table, not something we
    have to re-derive by re-parsing rendered HTML. This is what
    ``catalog.services_size_chart_backfill`` reads: one Algolia search
    request both locates the product and returns its chart, no second
    fetch of the product page needed.

    ``raw`` may be that JSON string, or an already-decoded list (tests pass
    the latter). Only the ``"inch"`` entry is used -- CM is derived from it
    at render time (x 2.54), same rule as the HTML-table path. Returns
    ``{}`` for anything that doesn't parse into the expected shape (missing
    field, malformed JSON, no "inch" entry) -- a product with no chart must
    degrade to "no chart" rather than raise."""
    if not raw:
        return {}
    data = raw
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except ValueError:
            return {}
    if not isinstance(data, list):
        return {}

    for entry in data:
        if not isinstance(entry, dict):
            continue
        unit = str(entry.get("unit_of_measurement", "")).strip().lower()
        chart = entry.get("chart")
        if unit != "inch" or not isinstance(chart, dict):
            continue
        result = {}
        for size, measurements in chart.items():
            if not isinstance(measurements, dict):
                continue
            parsed = {}
            for key, val in measurements.items():
                num = parse_bdt_price(str(val))
                if num is not None:
                    parsed[_slugify_size_chart_header(key)] = num
            if parsed:
                result[size] = parsed
        return result
    return {}


def parse_fabrilife_listing(html, base_url):
    """Parse a Fabrilife category "listing" into a list of absolute product
    page URLs (deduped, order preserved).

    ``html`` here is the raw JSON response body of an Algolia ``query``
    request against the site's own ``products`` index (see the module-level
    comment above for why -- the faceted ``/shop`` URL itself is a JS shell
    with no product links in its raw HTML). Each hit's ``id``/``slug`` are
    combined into the same ``/product/<id>-<slug>`` path the live site
    uses."""
    try:
        data = json.loads(html)
    except (ValueError, TypeError):
        return []
    urls = []
    for hit in data.get("hits", []):
        pid = hit.get("id")
        slug = hit.get("slug")
        if pid is None or not slug:
            continue
        urls.append(urljoin(base_url, f"product/{pid}-{slug}"))
    return _dedupe_preserve_order(urls)


# ---------------------------------------------------------------------------
# Rokomari (rokomari.com) -- a reference source, NOT a reseller partner (no
# sets_source_url, see catalog/models.py's ImportSource docstring and the
# 0009 data migration): imported products must never enter
# services_price_sync.sync_source_prices's re-pricing loop.
#
# Verified live 2026-07-30 against
# https://www.rokomari.com/product/category/2355/beauty-health (a plain
# server-rendered listing, ~309KB, 60 product cards) and one of its product
# pages (https://www.rokomari.com/product/210626/ashol-extra-virgin-olive-oil-
# joytun-tel-250ml):
#
# - Listing card: ``.product-card-wrapper``, its first ``<a href>`` is the
#   product URL (a second, later ``<a>`` in ``.home-details-btn-wrapper``
#   duplicates it -- ``card.find("a", href=True)`` picks the first, same
#   dedupe-by-URL approach as ``parse_opencart_listing``).
# - Product title: ``h1.title``.
# - Product price: ``.details-stationary__price`` (rendered twice in the raw
#   HTML -- once for a mobile toggle, once for desktop, both carrying
#   identical values, so ``select_one`` picking the first is fine) holding
#   ``span.sell-price`` (current/discounted price, always present) and,
#   only when discounted, ``strike.original-price`` (crossed-out original).
#   Deliberately NOT the ``.book-price``/``.original-price`` pair the listing
#   *card* markup uses for the same purpose -- that pair is reused verbatim
#   by the "Related/Similar Products" carousels further down a *product*
#   page, so selecting it there would silently grab an unrelated product's
#   price instead of this one's.
# - Brand: ``.details-stationary__brand a``.
# - Images: ``.details-stationary__thumbnil li[hovermax]`` -- the
#   ``hovermax`` attribute is the full-resolution image (1104x1581); the
#   ``<img src>`` in the same ``<li>`` is a 45x64 thumbnail.
# - Specifications: ``table.specification-section__table`` rows of
#   ``td.proDetailLabel``/``td.proDetailValue`` pairs; the header row (just
#   the "Specification" ``<h2>`` in a single ``<td>``) has neither class and
#   is skipped for free.
# - Description: ``.summary.ql-editor`` (a rich-text block headed "Summary"
#   followed by a "Key Features" list) -- there is no separate isolated
#   "Description" block on this theme; ``.about-description`` elsewhere on
#   the page is generic site-wide "About Rokomari" marketing copy repeated on
#   every page, not this product's text, and must not be used.
# - Prices are formatted "TK. 554" / "TK.554" (see the ``_TK_PREFIX_RE``
#   handling in ``parse_bdt_price`` above), not with the ৳ symbol.
#
# Listing CARD fields (as opposed to the product-page fields above) --
# ``parse_rokomari_listing_cards`` below, the affiliate picker's cheap path
# (see services_scrape_import.browse_candidates's detail=False branch, added
# to fix a live 502: fetching each of up to 12 product pages individually
# through polite_get at 1 req/sec took ~30s, past Render's gateway timeout).
# Each ``.product-card-wrapper`` (same card the URL-only parser above already
# selects) also carries, with NO further fetch:
# - Title: ``h4.book-title``.
# - Brand: ``p.book-author``, text "Brand: X" -- the "Brand: " prefix is
#   stripped.
# - Price: ``p.book-price`` holding ``strike.original-price`` (crossed-out
#   original, only when discounted) plus the current price as the element's
#   remaining bare text -- deliberately the SAME selector pair the big
#   comment above warns is reused by a product page's "Related/Similar
#   Products" carousel; that ambiguity only matters on a product page, and
#   this function only ever runs against a listing page.
# - Image: ``div.book-img img`` -- ``data-src`` (the real, lazy-loaded photo)
#   is used over ``src`` (a shared placeholder, ``non-book-default-image.png``
#   until the browser scrolls the card into view).
# ---------------------------------------------------------------------------


def _extract_rokomari_prices(soup):
    wrap = soup.select_one(".details-stationary__price")
    if wrap is None:
        return None, None
    sell = wrap.select_one(".sell-price")
    original = wrap.select_one(".original-price")
    sell_val = parse_bdt_price(sell.get_text()) if sell else None
    original_val = parse_bdt_price(original.get_text()) if original else None
    if original_val is not None and sell_val is not None:
        # Discounted: .sell-price is the lower, current price; .original-price
        # (a <strike>) is the crossed-out original -- same convention as
        # every other adapter in this module (price=original, discount_price=current).
        return original_val, sell_val
    if sell_val is not None:
        return sell_val, None
    return original_val, None


def _extract_rokomari_brand(soup):
    link = soup.select_one(".details-stationary__brand a")
    return link.get_text(strip=True) if link else ""


def _extract_rokomari_images(soup):
    urls = []
    for li in soup.select(".details-stationary__thumbnil li[hovermax]"):
        src = li.get("hovermax")
        if src:
            urls.append(_strip_query(src))
    return _dedupe_preserve_order(urls)


def _extract_rokomari_specifications(soup):
    specs = {}
    for row in soup.select("table.specification-section__table tr"):
        label = row.find("td", class_="proDetailLabel")
        value = row.find("td", class_="proDetailValue")
        if label and value:
            specs[label.get_text(strip=True)] = value.get_text(strip=True)
    return specs


def _extract_rokomari_description(soup):
    node = soup.select_one(".summary.ql-editor") or soup.select_one(".summary")
    if node is None:
        return ""
    return node.get_text(separator="\n", strip=True)


def parse_rokomari_product(html):
    """Parse a single rokomari.com product page into a plain dict with the
    same keys as ``parse_opencart_product`` (name, price, discount_price,
    description, specifications, brand, images). Pure function -- no
    network, no ORM (this module is imported by the runtime price-sync
    service and must stay side-effect-free)."""
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.select_one("h1.title") or soup.find("h1")
    name = h1.get_text(strip=True) if h1 else ""

    price, discount_price = _extract_rokomari_prices(soup)

    return {
        "name": name,
        "price": price,
        "discount_price": discount_price,
        "description": _extract_rokomari_description(soup),
        "specifications": _extract_rokomari_specifications(soup),
        "brand": _extract_rokomari_brand(soup),
        "images": _extract_rokomari_images(soup),
    }


def parse_rokomari_listing(html, base_url):
    """Parse a rokomari.com category or search-results listing page into a
    list of absolute product page URLs (deduped, order preserved). Both the
    category-browse page and the ``/search`` results page share the same
    ``.product-card-wrapper`` card markup."""
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    for card in soup.select(".product-card-wrapper"):
        link = card.find("a", href=True)
        if link:
            urls.append(urljoin(base_url, link["href"]))
    return _dedupe_preserve_order(urls)


def _extract_rokomari_listing_brand(card):
    el = card.select_one(".book-author")
    if el is None:
        return ""
    return _ROKOMARI_LISTING_BRAND_PREFIX_RE.sub("", el.get_text(strip=True)).strip()


def _extract_rokomari_listing_price(card):
    """Same original/discount convention as _extract_rokomari_prices: returns
    (price, discount_price) where price is the original (pre-discount) value
    and discount_price is the lower, current one -- None for discount_price
    when the item isn't discounted."""
    wrap = card.select_one(".book-price")
    if wrap is None:
        return None, None
    original = wrap.select_one(".original-price")
    original_val = parse_bdt_price(original.get_text()) if original else None
    full_text = wrap.get_text(" ", strip=True)
    if original is not None:
        # The current price is whatever text is left in .book-price after
        # removing the <strike> original's own text -- the markup has no
        # separate element for it (unlike the product-page price block).
        remainder = full_text.replace(original.get_text(" ", strip=True), "", 1).strip()
    else:
        remainder = full_text
    current_val = parse_bdt_price(remainder)
    if original_val is not None and current_val is not None:
        return original_val, current_val
    if current_val is not None:
        return current_val, None
    return original_val, None


def _extract_rokomari_listing_image(card):
    img = card.select_one(".book-img img")
    if img is None:
        return None
    src = img.get("data-src") or img.get("src")
    return _strip_query(src) if src else None


def parse_rokomari_listing_cards(html, base_url):
    """Parse a rokomari.com category/search listing page into structured
    candidate dicts (source_url, name, brand, price, discount_price, images)
    using ONLY the listing card markup -- no per-product fetch. Sibling to
    parse_rokomari_listing (which returns bare URLs for the per-product-
    detail-fetching path the catalog importer still uses); this is the cheap
    path for the affiliate picker -- see the module comment above and
    services_scrape_import.browse_candidates's detail=False branch."""
    soup = BeautifulSoup(html, "html.parser")
    out = []
    seen_urls = set()
    for card in soup.select(".product-card-wrapper"):
        link = card.find("a", href=True)
        if not link:
            continue
        url = urljoin(base_url, link["href"])
        if url in seen_urls:
            continue
        seen_urls.add(url)

        title_el = card.select_one(".book-title")
        name = title_el.get_text(strip=True) if title_el else ""
        price, discount_price = _extract_rokomari_listing_price(card)
        image = _extract_rokomari_listing_image(card)

        out.append({
            "source_url": url,
            "name": name,
            "brand": _extract_rokomari_listing_brand(card),
            "price": price,
            "discount_price": discount_price,
            "images": [image] if image else [],
        })
    return out


# --- arogga.com -------------------------------------------------------------
#
# Unlike every other adapter here, this one reads schema.org JSON-LD rather
# than CSS selectors. Arogga server-renders a complete `Product` blob on each
# product page and a `CollectionPage -> mainEntity(ItemList)` of full `Product`
# entries on each category page, so:
#
#   * browsing a category costs ONE request and still yields name, brand,
#     image, price and stock for every card -- no per-product fetch, and
#   * a site restyle cannot break the parse, only a schema change can.
#
# Migration 0008 seeded this source disabled with the note "client-rendered ...
# zero prices in the raw HTML". Re-verified 2026-08-07 against live pages: that
# is no longer the case. See catalog/test_fixtures/arogga_*.html, which are
# real captured payloads.

# Arogga states this in the page body, not in the JSON-LD. It drives
# Products.requires_prescription, which the checkout gate blocks while
# StoreConfiguration.rx_sales_enabled is False -- so a miss here would put
# prescription medicines on open sale. Matched case-insensitively against the
# de-tagged body so surrounding markup changes don't defeat it.
_RX_MARKER = "requires a prescription"


def _arogga_ld_blocks(html):
    """Every parseable ``application/ld+json`` payload on the page."""
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = tag.string or tag.get_text() or ""
        try:
            out.append(json.loads(raw.strip()))
        except (ValueError, TypeError):
            # One malformed block must not hide the rest of the page.
            continue
    return out


def _arogga_page_text(html):
    """Body text with scripts stripped, for markers that live outside JSON-LD."""
    without_scripts = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
    return " ".join(re.sub(r"<[^>]+>", " ", without_scripts).split())


def _arogga_offer_price(product):
    offers = product.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    price = offers.get("price")
    try:
        return float(price) if price not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _arogga_in_stock(product):
    offers = product.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    return str(offers.get("availability", "")).rstrip("/").split("/")[-1] == "InStock"


def _arogga_brand(product):
    brand = product.get("brand")
    if isinstance(brand, dict):
        return (brand.get("name") or "").strip()
    return (brand or "").strip() if isinstance(brand, str) else ""


def _arogga_images(product):
    image = product.get("image")
    if isinstance(image, list):
        return _dedupe_preserve_order([str(i) for i in image if i])
    return [str(image)] if image else []


def _arogga_product_fields(product, *, requires_prescription):
    """One JSON-LD ``Product`` -> the dict shape the other adapters return."""
    return {
        "name": (product.get("name") or "").strip(),
        "price": _arogga_offer_price(product),
        # Arogga publishes a single `offers.price`. There is no crossed-out
        # original, so reporting a discount would mean inventing one.
        "discount_price": None,
        "description": (product.get("description") or "").strip(),
        "specifications": {},
        "brand": _arogga_brand(product),
        "images": _arogga_images(product),
        "source_url": (product.get("url") or "").strip(),
        "source_sku": str(product.get("sku") or "").strip(),
        "source_category": (product.get("category") or "").strip(),
        "in_stock": _arogga_in_stock(product),
        "requires_prescription": requires_prescription,
    }


def parse_arogga_product(html):
    """Parse one arogga.com product page. Pure function -- no network, no ORM."""
    product = next((d for d in _arogga_ld_blocks(html) if d.get("@type") == "Product"), None)
    if not product:
        return {
            "name": "", "price": None, "discount_price": None, "description": "",
            "specifications": {}, "brand": "", "images": [], "source_url": "",
            "source_sku": "", "source_category": "", "in_stock": False,
            "requires_prescription": False,
        }
    rx = _RX_MARKER in _arogga_page_text(html).lower()
    return _arogga_product_fields(product, requires_prescription=rx)


def _arogga_listing_products(html):
    """The ``Product`` entries of a category page's nested ItemList.

    The list is NOT a top-level ItemList -- it hangs off
    ``CollectionPage.mainEntity``, which is why a naive "find @type ItemList"
    scan finds only the breadcrumb trail.
    """
    for block in _arogga_ld_blocks(html):
        entity = block.get("mainEntity") if isinstance(block, dict) else None
        candidates = []
        if isinstance(entity, dict) and entity.get("@type") == "ItemList":
            candidates = entity.get("itemListElement") or []
        elif block.get("@type") == "ItemList":
            candidates = block.get("itemListElement") or []
        products = [
            el["item"] for el in candidates
            if isinstance(el, dict) and isinstance(el.get("item"), dict)
            and el["item"].get("@type") == "Product"
        ]
        if products:
            return products
    return []


def parse_arogga_listing_cards(html, base_url):
    """Full candidates from a category page in a single request.

    A listing card cannot know whether an item needs a prescription -- that
    marker only exists on the product page -- so ``requires_prescription`` is
    reported as ``None`` ("unknown") rather than ``False``, which would read as
    a positive claim that the item is over-the-counter.
    """
    cards = []
    for product in _arogga_listing_products(html):
        fields = _arogga_product_fields(product, requires_prescription=None)
        if fields["source_url"]:
            fields["source_url"] = urljoin(base_url, fields["source_url"])
        cards.append(fields)
    seen, out = set(), []
    for card in cards:
        if card["source_url"] in seen:
            continue
        seen.add(card["source_url"])
        out.append(card)
    return out


def parse_arogga_listing(html, base_url):
    """Absolute product URLs from a category page (deduped, order preserved)."""
    return [c["source_url"] for c in parse_arogga_listing_cards(html, base_url) if c["source_url"]]
