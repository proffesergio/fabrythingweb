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
from decimal import Decimal, InvalidOperation

import requests
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from catalog.models import Products, ProductVariant
from catalog.pricing import apply_markup, quote_supplier_price

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
    from catalog.supplier_security import supplier_get_bytes
    try:
        image_bytes = supplier_get_bytes(url, max_bytes=5_000_000)
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
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
                       sku_hint=None, sku_prefix=SKU_PREFIX, pricing_policy=None):
    """Create or update one ``Products`` row (+ its ``ProductVariant`` rows)
    from a plain-dict ``entry`` (same shape the scrape fixtures use: name,
    price, discount_price, description, specifications, brand, gender,
    material, sizes, size_chart, images -- raw source image URLs, downloaded
    here -- source_url).

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
        price_decimal = Decimal(str(entry.get('price')))
        price = price_decimal if price_decimal.is_finite() and price_decimal > 0 else None
    except (TypeError, ValueError, InvalidOperation):
        price = None
    if price is None:
        return {"status": "skipped_invalid", "reason": "missing price",
                "product": None, "slug": slugify(name)[:250], "sku_n_used": None}

    slug = slugify(name)[:250]
    existing = Products.objects.filter(slug=slug).first()
    if existing is not None and not force:
        return {"status": "skipped_exists", "reason": "already in store",
                "product": existing, "slug": slug, "sku_n_used": None}

    try:
        discount_decimal = Decimal(str(entry['discount_price'])) if entry.get('discount_price') else None
        disc = discount_decimal if discount_decimal is not None and discount_decimal.is_finite() and 0 < discount_decimal < price_decimal else None
    except (TypeError, ValueError, InvalidOperation):
        disc = None
    weight = entry.get('weight_grams')
    shipping = entry.get('shipping_fee')
    try:
        if weight is not None and (Decimal(str(weight)) < 0 or Decimal(str(weight)) > 100000 or not Decimal(str(weight)).is_finite()):
            raise ValueError('Invalid weight')
        if shipping is not None and (Decimal(str(shipping)) < 0 or Decimal(str(shipping)) > Decimal('999999.99') or not Decimal(str(shipping)).is_finite()):
            raise ValueError('Invalid shipping fee')
    except (TypeError, InvalidOperation, ValueError):
        return {"status": "skipped_invalid", "reason": "invalid weight or shipping fee", "product": None, "slug": slug, "sku_n_used": None}
    try:
        quote = quote_supplier_price(price, pricing_policy, weight_grams=weight)
        discount_quote = quote_supplier_price(disc, pricing_policy, weight_grams=weight) if disc else None
    except ValueError as exc:
        return {"status": "skipped_invalid", "reason": str(exc), "product": None, "slug": slug, "sku_n_used": None}

    images = [u for u in (image_fn(src) for src in entry.get("images", [])[:3]) if u]

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
        "size_chart": entry.get("size_chart") or {},
        "image": images,
        "initial_buying_price": round(quote['base_price'] * Decimal('0.85')),  # dealer-price placeholder
        "base_price": quote['base_price'],
        "initial_selling_price": quote['selling_price'],
        "discount_price": discount_quote['selling_price'] if discount_quote else None,
        # Medicines only. Products.requires_prescription is what the checkout
        # gate keys on while StoreConfiguration.rx_sales_enabled is False, so
        # dropping it here would put prescription-only items on open sale.
        # bool() because a listing card reports None ("unknown"), which must
        # settle to False rather than raise.
        "requires_prescription": bool(entry.get("requires_prescription")),
        "source_url": entry.get("source_url") or "",
        "source_price": price if entry.get("source_url") or pricing_policy else None,
        "source_currency": quote['source_currency'] if pricing_policy else 'BDT',
        "price_synced_at": timezone.now() if entry.get("source_url") else None,
        "category_id": category,
        "status": "ACTIVE",
        "domain_user_id": domain_user,
        "added_by_user_id": added_by_user,
        "seo_title": f"{name} - Fabrything",
        "seo_description": (entry.get("description") or name)[:160],
    }
    if shipping is not None:
        defaults['shipping_fee'] = Decimal(str(shipping))
    if weight is not None:
        defaults['weight'] = float(Decimal(str(weight)) / Decimal('1000'))

    # Commit the product and checkout-facing variants as one price change.
    with transaction.atomic():
        sku_n_used = None
        if existing is not None:
            # --force-update keeps the assigned SKU even as prices change.
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

        # Checkout snapshots ProductVariant.effective_price, so update it in
        # the same transaction as the product shelf price.
        variant_price = discount_quote['selling_price'] if discount_quote else quote['selling_price']
        sizes = entry.get("sizes") or [""]
        for size in sizes:
            variant, variant_created = ProductVariant.objects.get_or_create(
                product=product, size=size, color="",
                defaults={"sku": f"{product.sku}-{size or 'DEF'}",
                          "price": variant_price, "stock_quantity": 25,
                          "weight_grams": int(Decimal(str(weight))) if weight is not None else 0})
            if force and not variant_created:
                variant.price = variant_price
                variant.discount_price = None
                variant.save(update_fields=["price", "discount_price", "updated_at"])

        from storeops.models import OperationsPolicy
        if OperationsPolicy.current().auto_clean_images:
            from storeops.images import enqueue_product
            enqueue_product(product)

    return {"status": status, "reason": None, "product": product,
            "slug": slug, "sku_n_used": sku_n_used}
