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
