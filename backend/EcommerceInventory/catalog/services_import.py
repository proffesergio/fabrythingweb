"""Shared "product entry -> Products + ProductVariant" import logic.

Extracted from ``catalog.management.commands.seed_store_catalog._seed_products``
so both the fixture-file seeder *and* the admin browse/import endpoints
(``catalog.services_scrape_import``) funnel through one create/update path
and can't drift apart -- see CLAUDE.md's "Store catalog seeding" note and the
seed_bancharampur lesson it references.

``seed_product_entry`` is deliberately create-only by default (``force=False``):
importing something already present skips it rather than duplicating or
overwriting -- that is what the admin import endpoint needs (idempotent
re-import). ``seed_store_catalog`` opts into ``force=True`` refresh behaviour
with ``--force-update``, matching its pre-extraction behaviour exactly.
"""
import io
import os

import requests
from django.utils import timezone
from django.utils.text import slugify

from catalog.models import Products, ProductVariant
from catalog.pricing import apply_markup

SKU_PREFIX = "FS"


def import_image(url, on_error=None):
    """Download -> compress (max 800x800 JPEG q80) -> our storage.

    Never hotlink a source site's image: every URL supplied gets downloaded
    once, recompressed to an affordable size, and re-uploaded to our own
    storage; only our own URL is ever stored on the product. Returns None on
    any failure so one bad image never sinks the whole import.
    """
    from PIL import Image

    from core.storage import save_file
    try:
        r = requests.get(url, timeout=20,
                         headers={"User-Agent": "Mozilla/5.0 (fabrything import)"})
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        img.thumbnail((800, 800))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=80, optimize=True)
        name = os.urandom(12).hex() + ".jpg"
        return save_file(name, buf.getvalue(), "image/jpeg")
    except Exception as e:  # noqa: BLE001 -- a bad image must never sink the import
        if on_error is not None:
            on_error(url, e)
        return None


def next_sku(n, prefix=SKU_PREFIX):
    """Return the first unused ``<prefix>-<n>`` SKU at or after ``n``.

    A caller-supplied starting hint is only ever a *hint* (an admin can
    rename a SKU away from the prefix, delete a row, or a previous run can
    leave gaps) -- checking existence at the point of assignment, and
    advancing past any collision, is what actually guarantees uniqueness.
    """
    while Products.objects.filter(sku=f"{prefix}-{n}").exists():
        n += 1
    return n


def seed_product_entry(entry, category, domain_user, added_by_user=None, *,
                       force=False, import_image_fn=None,
                       sku_hint=None, sku_prefix=SKU_PREFIX):
    """Create or update one ``Products`` row (+ its ``ProductVariant`` rows)
    from a plain-dict ``entry`` (same shape the scrape fixtures use: name,
    price, discount_price, description, specifications, brand, gender,
    material, sizes, images -- raw source image URLs, downloaded here --
    source_url).

    ``category`` is an already-resolved ``Categories`` instance. ``domain_user``
    owns the row (``Products.domain_user_id``); ``added_by_user`` records who
    actually performed the import (``Products.added_by_user_id``) and
    defaults to ``domain_user`` when not given, matching the single-owner
    seed-command behaviour.

    Never creates a product with no name or no sellable price -- returns a
    "skipped_invalid" result instead, the way the offline scrape tools
    already refuse to write such an entry to a fixture.

    Returns a dict: ``{"status": "created"|"updated"|"skipped_exists"|
    "skipped_invalid", "reason": str|None, "product": Products|None,
    "slug": str, "sku_n_used": int|None}``. ``sku_n_used`` is only set when a
    new row was created, so a caller seeding many entries in one run (the
    management command) can advance its own running SKU counter without a
    fresh COUNT query per row.
    """
    added_by_user = added_by_user or domain_user
    # A bare `import_image_fn=import_image` default parameter would bind to
    # the function object at *def* time, so unittest.mock.patch("catalog.
    # services_import.import_image", ...) in a caller-agnostic test would
    # never take effect. Resolving the module-global by name at call time
    # instead means a patch of this module's own `import_image` attribute is
    # honoured regardless of which caller (seed_store_catalog,
    # services_scrape_import) invokes this function.
    image_fn = import_image_fn or import_image

    name = (entry.get("name") or "").strip()
    if not name:
        return {"status": "skipped_invalid", "reason": "missing name",
                "product": None, "slug": "", "sku_n_used": None}

    try:
        price = float(entry.get("price")) if entry.get("price") else None
    except (TypeError, ValueError):
        price = None
    if not price:
        return {"status": "skipped_invalid", "reason": "missing price",
                "product": None, "slug": slugify(name)[:250], "sku_n_used": None}

    slug = slugify(name)[:250]
    existing = Products.objects.filter(slug=slug).first()
    if existing is not None and not force:
        return {"status": "skipped_exists", "reason": "already in store",
                "product": existing, "slug": slug, "sku_n_used": None}

    images = [u for u in (image_fn(src) for src in entry.get("images", [])[:3]) if u]

    try:
        disc = float(entry["discount_price"]) if entry.get("discount_price") else None
    except (TypeError, ValueError):
        disc = None

    # `price`/`disc` are the SOURCE's raw pre-markup numbers -- they become
    # base_price (recoverable forever) and the selling/discount prices are
    # always derived from them through apply_markup, never mutated in place.
    # See catalog/pricing.py: this is the one rule every price-setting path
    # in the catalog (import, seed_store_catalog, sync_source_prices, the
    # apply_pricing_markup backfill) goes through.
    defaults = {
        "name": name,
        "description": entry.get("description") or name,
        "specifications": entry.get("specifications") or {},
        "brand": entry.get("brand") or "",
        "gender": entry.get("gender") or "UNISEX",
        "material": entry.get("material") or "",
        "available_sizes": entry.get("sizes") or [],
        "image": images,
        "initial_buying_price": round(price * 0.85),  # dealer-price placeholder
        "base_price": price,
        "initial_selling_price": apply_markup(price),
        "discount_price": apply_markup(disc) if disc else None,
        "source_url": entry.get("source_url") or "",
        "source_price": price if entry.get("source_url") else None,
        "price_synced_at": timezone.now() if entry.get("source_url") else None,
        "category_id": category,
        "status": "ACTIVE",
        "domain_user_id": domain_user,
        "added_by_user_id": added_by_user,
        "seo_title": f"{name} - Fabrything",
        "seo_description": (entry.get("description") or name)[:160],
    }

    sku_n_used = None
    if existing is not None:
        # --force-update: refresh the admin-visible fields, but never
        # regenerate the SKU -- it's an identity assigned once at creation,
        # not fixture data, and other records (POs, invoices) may reference
        # it.
        for field, value in defaults.items():
            setattr(existing, field, value)
        existing.save()
        product = existing
        status = "updated"
    else:
        start = sku_hint if sku_hint is not None else (
            1000 + Products.objects.filter(sku__startswith=sku_prefix).count())
        sku_n_used = next_sku(start, sku_prefix)
        product = Products.objects.create(
            slug=slug, sku=f"{sku_prefix}-{sku_n_used}", **defaults)
        status = "created"

    # Checkout charges ProductVariant.effective_price, not this Products row
    # (orders/services.py), so the variant must carry the same marked-up
    # number the product does. `disc or price` was the pre-markup "what the
    # customer actually pays" value; mark that same value up so the two never
    # disagree.
    variant_price = apply_markup(disc if disc else price)
    sizes = entry.get("sizes") or [""]
    for size in sizes:
        variant, variant_created = ProductVariant.objects.get_or_create(
            product=product, size=size, color="",
            defaults={"sku": f"{product.sku}-{size or 'DEF'}",
                      "price": variant_price, "stock_quantity": 25})
        # get_or_create only applies `defaults` on creation, so a forced
        # re-seed never used to touch an existing variant's price -- checkout
        # charges the variant (effective_price), so the storefront would show
        # the new price while checkout kept charging the stale one. On
        # force, refresh it explicitly.
        if force and not variant_created:
            variant.price = variant_price
            variant.save(update_fields=["price", "updated_at"])

    return {"status": status, "reason": None, "product": product,
            "slug": slug, "sku_n_used": sku_n_used}
