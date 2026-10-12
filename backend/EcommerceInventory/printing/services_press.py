"""Web-to-press pricing + fulfilment helpers (ColorLifePrint-style).

The spec formula lives here and ONLY here::

    Total = (Base Setup + Per-Unit Material * Qty + Finishing Add-ons) * Margin

with the quantity-tier bulk discount applied to the material leg before the
margin factor. Both the public quote preview and the checkout snapshot call
``compute_press_quote``, so the estimate on the form can never disagree with
what gets booked — the same guarantee ``printing.services.compute_quote``
makes for the garment flow.
"""
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction

DEFAULT_ALLOWED_EXTENSIONS = ["pdf", "ai", "psd", "eps", "tiff", "tif", "png", "jpeg", "jpg"]
SIDES_FACTORS = {"4/0": Decimal("1.0"), "4/4": Decimal("1.8")}
MONEY = Decimal("0.01")


def money(value):
    return Decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP)


def to_sq_inch(width, height, unit="in"):
    """Finished trim area in square inches. Custom sizes arrive in in/ft/mm."""
    w, h = Decimal(width), Decimal(height)
    if unit == "ft":
        w, h = w * 12, h * 12
    elif unit == "mm":
        w, h = w / Decimal("25.4"), h / Decimal("25.4")
    return w * h


def discount_percent_for(quantity, product=None):
    """Per-product tier override wins; otherwise the global ladder."""
    tiers = None
    if product is not None and getattr(product, "quantity_tiers", None):
        tiers = product.quantity_tiers
    if not tiers:
        from printing.models import PrintPricingConfig

        tiers = PrintPricingConfig.get_solo().quantity_tiers or []
    best = Decimal("0")
    for tier in sorted(tiers, key=lambda t: (t or {}).get("min_qty", 0)):
        if quantity >= (tier or {}).get("min_qty", 0):
            best = Decimal(str((tier or {}).get("discount_percent", 0)))
    return best


def reference_area_sq_inch(product):
    preset = product.size_presets.filter(is_active=True).order_by("display_order").first()
    if preset is None:
        return Decimal("1")
    return to_sq_inch(preset.width, preset.height, preset.unit) or Decimal("1")


def compute_press_quote(*, product, width, height, unit="in",
                        paper_stock=None, finishing_options=None,
                        quantity=1, sides="4/0"):
    """Full priced breakdown (all BDT). Pure function — no DB writes."""
    from printing.models import PressShopConfig

    quantity = max(1, int(quantity or 1))
    area = to_sq_inch(width, height, unit)
    sides = sides if sides in SIDES_FACTORS else "4/0"
    sides_factor = SIDES_FACTORS[sides]
    finishings = list(finishing_options or [])

    if Decimal(product.per_sq_inch_rate) > 0:
        base_material = Decimal(product.per_sq_inch_rate) * area
    else:
        ref = reference_area_sq_inch(product)
        base_material = Decimal(product.per_unit_material_cost) * (area / ref)

    multiplier = Decimal(paper_stock.multiplier) if paper_stock else Decimal("1")
    flat_addon = Decimal(paper_stock.flat_addon_per_unit) if paper_stock else Decimal("0")
    material_per_unit = base_material * multiplier * sides_factor + flat_addon

    material_leg = material_per_unit * quantity
    discount_percent = discount_percent_for(quantity, product)
    discount_amount = money(material_leg * discount_percent / Decimal("100"))
    material_net = material_leg - discount_amount

    finishing_per_unit = sum(
        (Decimal(f.price) for f in finishings if f.per_unit), Decimal("0"),
    )
    finishing_flat = sum(
        (Decimal(f.price) for f in finishings if not f.per_unit), Decimal("0"),
    )
    finishing_addons = finishing_per_unit * quantity + finishing_flat

    base_setup = Decimal(product.base_setup_cost)
    subtotal = base_setup + material_net + finishing_addons
    margin = product.effective_margin()
    total = money(subtotal * margin)
    config = PressShopConfig.get_solo()

    return {
        "area_sq_inch": area,
        "material_per_unit": money(material_per_unit),
        "material_leg": money(material_leg),
        "discount_percent": discount_percent,
        "discount_amount": discount_amount,
        "material_net": money(material_net),
        "finishing_addons": money(finishing_addons),
        "base_setup": money(base_setup),
        "subtotal": money(subtotal),
        "margin_factor": margin,
        "total_bdt": total,
        "usd_rate": config.usd_rate,
        "total_usd": money(total / config.usd_rate) if config.usd_rate else total,
    }


def convert_currency(total_bdt, currency="BDT"):
    from printing.models import PressShopConfig

    total_bdt = Decimal(total_bdt)
    if currency == "USD":
        rate = PressShopConfig.get_solo().usd_rate or Decimal("1")
        return money(total_bdt / rate)
    return money(total_bdt)


def shipping_quote(*, weight_kg, zone, courier=""):
    """Weight + location based fee. Explicit PressShippingRate rows win,
    otherwise the PressShopConfig.shipping_matrix fallback (BDT)."""
    from printing.models import PressShippingRate, PressShopConfig

    weight_kg = Decimal(weight_kg or 0)
    rows = PressShippingRate.objects.filter(zone=zone, is_active=True)
    if courier:
        rows = rows.filter(courier__iexact=courier)
    row = rows.order_by("base_fee").first()
    if row:
        return {
            "fee_bdt": money(row.quote_for(weight_kg)),
            "courier": row.courier,
            "zone": zone,
        }
    matrix = PressShopConfig.get_solo().shipping_matrix or {}
    key = {"INSIDE_DHAKA_HOME": "inside_dhaka_home", "HUB_PICKUP": "hub_pickup"}.get(zone, "outside_dhaka")
    base = Decimal(str(matrix.get(key, 0)))
    per_kg = Decimal(str(matrix.get("per_kg", 0)))
    default_courier = {
        "INSIDE_DHAKA_HOME": "Steadfast", "HUB_PICKUP": "Hub Pickup",
    }.get(zone, "Sundarban Courier")
    return {"fee_bdt": money(base + per_kg * weight_kg), "courier": courier or default_courier, "zone": zone}


def validate_artwork(files_meta, *, width, height, unit="in", product=None):
    """Server-side artwork validation report.

    ``files_meta`` is a list of {"name", "size", "content_type",
    "width_px", "height_px"} (pixel dims optional — the client sends them when
    it can read the image). Checks: extension allow-list, per-file size cap,
    aspect-ratio match vs the trim size, and a 300-DPI estimate. Never raises;
    returns a report the checkout stores on the order and the admin reviews.
    """
    from printing.models import PressShopConfig

    config = PressShopConfig.get_solo()
    max_bytes = int(config.max_upload_mb or 100) * 1024 * 1024
    allowed = set((product.allowed_extensions if product and product.allowed_extensions else DEFAULT_ALLOWED_EXTENSIONS))
    allowed = {str(e).lower().lstrip(".") for e in allowed}

    warnings = []
    files_ok = True
    dpi_values = []
    aspect_ok = True

    trim_w, trim_h = Decimal(width or 0), Decimal(height or 0)
    trim_ratio = None
    if trim_w > 0 and trim_h > 0:
        trim_ratio = float(trim_w / trim_h)

    for f in files_meta or []:
        name = str((f or {}).get("name", ""))
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        size = int((f or {}).get("size") or 0)
        if ext not in allowed:
            warnings.append(f"{name or 'File'}: .{ext or '?'} is not an accepted format.")
            files_ok = False
        if size > max_bytes:
            warnings.append(f"{name or 'File'} exceeds the {config.max_upload_mb}MB limit.")
            files_ok = False
        w_px, h_px = (f or {}).get("width_px"), (f or {}).get("height_px")
        if w_px and h_px and trim_w > 0 and trim_h > 0:
            try:
                file_ratio = float(Decimal(w_px) / Decimal(h_px))
                if trim_ratio and abs(file_ratio - trim_ratio) / max(trim_ratio, 0.01) > 0.02:
                    aspect_ok = False
                    warnings.append(
                        f"{name or 'File'}: aspect ratio does not match "
                        f"the selected {trim_w}x{trim_h}{unit} size.",
                    )
                # DPI estimate against the trim size in inches.
                area_unit = unit
                trim_w_in = float(trim_w) * (12 if area_unit == "ft" else (1 / 25.4 if area_unit == "mm" else 1))
                dpi = float(w_px) / trim_w_in if trim_w_in else 0
                dpi_values.append(round(dpi, 1))
                if dpi < 300:
                    warnings.append(
                        f"{name or 'File'}: ~{dpi:.0f} DPI at print size — "
                        f"300 DPI or higher is recommended.",
                    )
            except Exception:
                warnings.append(f"{name or 'File'}: could not verify DPI/aspect ratio.")

    min_dpi = min(dpi_values) if dpi_values else None
    return {
        "ok": files_ok and aspect_ok,
        "warnings": warnings,
        "aspect_ok": aspect_ok,
        "min_dpi": min_dpi,
        "low_dpi": bool(min_dpi is not None and min_dpi < 300),
        "checked_files": len(files_meta or []),
    }


@transaction.atomic
def create_press_order(customer, *, product, width, height, unit="in",
                       paper_stock=None, finishing_ids=None, quantity=1,
                       sides="4/0", currency="BDT", payment_method="SSLCOMMERZ",
                       shipping_zone="INSIDE_DHAKA_HOME", shipping_courier="",
                       shipping_address=None, artwork_files=None,
                       artwork_meta=None, size_name="", po_number="",
                       is_corporate=False, quotation=None):
    """Price, snapshot and book a PressOrder in PENDING_PAYMENT.

    The price breakdown is frozen here so later catalogue edits never move a
    booked order's books (same rule the garment approval snapshot follows).
    """
    from rest_framework.exceptions import ValidationError

    from printing.models import FinishingOption, PressOrder

    if quantity < product.min_qty:
        raise ValidationError(f"Minimum order for {product.name} is {product.min_qty} pcs.")
    if payment_method == "PARTIAL_ADVANCE":
        account = getattr(customer, "corporate_account", None)
        if account is None or not account.trusted_for_partial or not account.is_active:
            raise ValidationError("Partial advance is only available to trusted corporate accounts.")

    finishings = list(FinishingOption.objects.filter(pk__in=finishing_ids or [], is_active=True))
    quote = compute_press_quote(
        product=product, width=width, height=height, unit=unit,
        paper_stock=paper_stock, finishing_options=finishings,
        quantity=quantity, sides=sides,
    )
    weight_kg = Decimal(product.weight_per_unit_kg or 0) * quantity
    ship = shipping_quote(weight_kg=weight_kg, zone=shipping_zone, courier=shipping_courier or "")
    total_bdt = quote["total_bdt"] + ship["fee_bdt"]

    report = validate_artwork(
        artwork_meta or [], width=width, height=height, unit=unit, product=product,
    )
    breakdown = {
        k: str(v) for k, v in quote.items()
        if k not in ("area_sq_inch",)
    }
    breakdown.update({
        "area_sq_inch": str(quote["area_sq_inch"]),
        "shipping_fee_bdt": str(ship["fee_bdt"]),
        "shipping_courier": ship["courier"],
        "weight_kg": str(weight_kg),
    })

    order = PressOrder.objects.create(
        customer=customer,
        product=product,
        paper_stock=paper_stock,
        size_name=size_name or f"{width}x{height}{unit}",
        width=width, height=height, size_unit=unit,
        sides=sides, quantity=quantity,
        price_breakdown=breakdown,
        total_bdt=total_bdt,
        currency=currency if currency in ("BDT", "USD") else "BDT",
        total_charged=convert_currency(total_bdt, currency),
        payment_method=payment_method,
        payment_status="COD_DUE" if payment_method == "COD" else "PENDING",
        shipping_zone=shipping_zone,
        shipping_courier=ship["courier"],
        shipping_fee_bdt=ship["fee_bdt"],
        shipping_address=dict(shipping_address or {}),
        artwork_files=list(artwork_files or []),
        artwork_validation=report,
        is_corporate=is_corporate,
        po_number=po_number or "",
    )
    order.finishing_options.set(finishings)
    if payment_method == "COD":
        # No online payment to wait for — straight into the artwork queue.
        order.transition_to(PressOrder.Status.ARTWORK_REVIEW)
    if quotation is not None:
        quotation.press_order = order
        quotation.status = "ORDERED"
        quotation.save(update_fields=["press_order", "status", "updated_at"])
    if is_corporate:
        account = getattr(customer, "corporate_account", None)
        if account is not None:
            account.ledger_balance_bdt = Decimal(account.ledger_balance_bdt) + total_bdt
            account.save(update_fields=["ledger_balance_bdt", "updated_at"])
    return order


def init_payment(order):
    """Stub gateway init: returns {gateway_url, txn_id} and stamps the order.

    Real SSLCommerz/bKash/Nagad/Rocket credentials plug in here; the shape
    (redirect URL + transaction id, then a separate callback) already matches
    all four providers so the storefront needs no changes when keys land.
    """
    import uuid

    txn_id = f"{order.payment_method[:3]}-{order.pk}-{uuid.uuid4().hex[:10].upper()}"
    order.payment_txn_id = txn_id
    order.save(update_fields=["payment_txn_id", "updated_at"])
    return {"gateway_url": f"/press/payment/{order.pk}/?txn={txn_id}", "txn_id": txn_id}


def handle_payment_callback(order, *, success, amount=None, txn_id=""):
    """Gateway callback: success moves PENDING_PAYMENT -> ARTWORK_REVIEW and
    stamps PAID (or PARTIAL for partial-advance corporate top-ups). Failure
    stamps FAILED with a clear message the storefront surfaces verbatim."""
    from rest_framework.exceptions import ValidationError

    from printing.models import PressOrder

    if txn_id:
        order.payment_txn_id = txn_id
    if success:
        if order.payment_method == "PARTIAL_ADVANCE":
            order.payment_status = "PARTIAL"
        else:
            order.payment_status = "PAID"
        order.save(update_fields=["payment_status", "payment_txn_id", "updated_at"])
        if order.status == PressOrder.Status.PENDING_PAYMENT:
            order.transition_to(PressOrder.Status.ARTWORK_REVIEW)
        return order
    order.payment_status = "FAILED"
    order.save(update_fields=["payment_status", "payment_txn_id", "updated_at"])
    raise ValidationError(
        "Payment failed or was cancelled. No amount was charged — "
        "please retry or choose Cash on Delivery.",
    )


@transaction.atomic
def create_quotation(customer, *, product, width, height, unit="in",
                     paper_stock=None, finishing_ids=None, quantity=1,
                     sides="4/0", currency="BDT", po_number=""):
    from printing.models import FinishingOption, Quotation

    finishings = list(FinishingOption.objects.filter(pk__in=finishing_ids or [], is_active=True))
    quote = compute_press_quote(
        product=product, width=width, height=height, unit=unit,
        paper_stock=paper_stock, finishing_options=finishings,
        quantity=quantity, sides=sides,
    )
    weight_kg = Decimal(product.weight_per_unit_kg or 0) * quantity
    config = {
        "product_id": product.id, "product_name": product.name,
        "width": str(width), "height": str(height), "unit": unit,
        "paper_stock_id": paper_stock.id if paper_stock else None,
        "paper_stock_name": paper_stock.name if paper_stock else None,
        "finishing_ids": [f.id for f in finishings],
        "finishing_names": [f.name for f in finishings],
        "quantity": quantity, "sides": sides,
        "weight_kg": str(weight_kg),
    }
    breakdown = {k: str(v) for k, v in quote.items()}
    return Quotation.objects.create(
        customer=customer, product=product,
        config_snapshot=config, price_breakdown=breakdown,
        total_bdt=quote["total_bdt"],
        currency=currency if currency in ("BDT", "USD") else "BDT",
        po_number=po_number or "",
    )
