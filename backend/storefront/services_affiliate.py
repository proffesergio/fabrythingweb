"""Link construction for AffiliateProduct -- the reverse-engineered Rokomari
attribution scheme, plus the small helper that extracts a Rokomari product id
out of a product-page URL for the admin search/bulk-add flow.

Rokomari's affiliate dashboard only hands out an opaque rkmri.co/<random>
short link with no way to construct one ourselves. Resolving one showed it
302s to a plain parameterised URL::

    https://rkmri.co/R5MEpp0p0IEI/  ->
    https://www.rokomari.com/quick-cart?affId=Ma8A710222i0iRo&affs=70278
        &cma=604800&productId=531074

so attribution rides on ordinary query parameters -- we can build a link for
ANY product ourselves, no per-product dashboard round-trip needed.
Product-page links (as opposed to the quick-cart link above) use the same
affId/affs/cma params on a /product/<id>/<slug> URL -- verified live
(2026-07-30, via WebFetch) that a real Rokomari product page renders normally
with those params appended (full product detail page, no error, no stripped
params, params simply ignored by the page itself); genuine click-to-cookie
attribution cannot be confirmed from here without the owner's own Rokomari
affiliate dashboard, since that requires an authenticated session on their
side.

This is reverse-engineered, not contracted: never hardcode affId/affs/cma or
the base URL anywhere else -- AffiliateConfig.get_solo() is the only source,
and a manual_short_link on the product always wins over anything built here.
"""
import re
from urllib.parse import urlencode

from django.utils.text import slugify

from .models import AffiliateConfig

# Matches the numeric id segment of a Rokomari product-detail URL, e.g.
# ".../product/210626/ashol-..." -> "210626". Deliberately requires digits
# immediately after "/product/" so a category listing URL
# (".../product/category/2355/beauty-health") never matches -- "category"
# isn't digits.
_ROKOMARI_PRODUCT_ID_RE = re.compile(r"/product/(\d+)(?:[/?#]|$)")


def extract_rokomari_product_id(url):
    """Pull the numeric productId out of a rokomari.com product page URL.
    Returns None if the URL doesn't look like a product page (e.g. it's a
    category listing or something unrelated)."""
    if not url:
        return None
    m = _ROKOMARI_PRODUCT_ID_RE.search(url)
    return m.group(1) if m else None


class UnsupportedProgramError(ValueError):
    """Raised when a product's `program` has no link-building adapter and no
    manual_short_link override -- fail loudly rather than send a customer to
    a broken/blank URL."""


def build_affiliate_link(product) -> str:
    """Resolve the outbound URL for one AffiliateProduct.

    A manual_short_link override always wins (see AffiliateProduct's
    docstring) -- this is the owner's escape hatch if the constructed scheme
    ever stops attributing, so it must never be second-guessed here.
    """
    if product.manual_short_link:
        return product.manual_short_link
    if product.program == "rokomari":
        return _rokomari_link(product)
    raise UnsupportedProgramError(
        f"No link-building adapter for affiliate program {product.program!r} "
        f"and no manual_short_link override is set.")


def _rokomari_link(product) -> str:
    config = AffiliateConfig.get_solo()
    base = config.base_url.rstrip("/") + "/"
    params = {
        "affId": config.affiliate_id,
        "affs": config.sub_id,
        "cma": config.cookie_window_seconds,
    }
    if product.link_type == "PRODUCT":
        slug = slugify(product.title or "")[:200] or "product"
        path = f"product/{product.remote_product_id}/{slug}"
        return f"{base}{path}?{urlencode(params)}"
    # CART (default): the quick-cart/quick-buy link -- what a resolved
    # rkmri.co short link actually turned out to be.
    params["productId"] = product.remote_product_id
    return f"{base}quick-cart?{urlencode(params)}"
