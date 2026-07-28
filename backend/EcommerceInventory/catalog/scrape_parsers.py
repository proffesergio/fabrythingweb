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
"""
import json
import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

_PRICE_RE = re.compile(r"[\d,]+(?:\.\d+)?")


def parse_bdt_price(text):
    """Parse a BDT price string like ``"8,500৳"`` or ``"৳ 12,990"``
    into a float. Returns ``None`` when the text has no digits (e.g. "Out of
    stock")."""
    if not text:
        return None
    m = _PRICE_RE.search(text.replace("৳", "").strip())  # strip Taka sign
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


def _extract_brand(soup):
    for row in soup.select(".product-wid-info"):
        label = row.find("p")
        if label and "brand" in label.get_text(strip=True).lower():
            link = row.find("a")
            if link:
                return link.get_text(strip=True)
    return ""


def _extract_prices(soup):
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


def _extract_images(soup, base_url):
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


def _extract_specifications(soup):
    specs = {}
    for row in soup.select("table.data-table tr"):
        name = row.find("td", class_="name")
        value = row.find("td", class_="value")
        if name and value:
            specs[name.get_text(strip=True)] = value.get_text(strip=True)
    return specs


def _extract_description(soup):
    node = soup.select_one("#description .descriptionContent") or soup.select_one("#description")
    if node is None:
        return ""
    text = node.get_text(separator="\n", strip=True)
    return text


def parse_opencart_product(html):
    """Parse a single OpenCart product page into a plain dict with keys:
    name, price, discount_price, description, specifications, brand, images
    (absolute URLs).

    The base URL for resolving image ``src`` attributes is read from the
    page's own ``<base href>`` tag -- present on every OpenCart page served
    by this theme -- so callers only need to pass the page HTML."""
    soup = BeautifulSoup(html, "html.parser")

    base_tag = soup.find("base", href=True)
    base_url = base_tag["href"] if base_tag else ""

    h1 = soup.select_one("h1.product_title") or soup.find("h1")
    name = h1.get_text(strip=True) if h1 else ""

    price, discount_price = _extract_prices(soup)

    return {
        "name": name,
        "price": price,
        "discount_price": discount_price,
        "description": _extract_description(soup),
        "specifications": _extract_specifications(soup),
        "brand": _extract_brand(soup),
        "images": _extract_images(soup, base_url),
    }


def parse_opencart_listing(html, base_url):
    """Parse an OpenCart category listing page into a list of absolute
    product page URLs (deduped, order preserved)."""
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    for card in soup.select(".product-item"):
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
    (``"MEN"``/``"WOMEN"``/``"KIDS"``), ``sizes`` (list) and ``material``
    (``""`` when the description doesn't state it)."""
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
    }


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
