# Seed the web-to-press catalogue: products, sizes, paper stocks, finishing
# options and BD courier rates. Idempotent (get_or_create) so re-runs and
# existing installs are safe; staff can retune everything from the admin.
from decimal import Decimal

from django.db import migrations


PRODUCTS = [
    {"name": "Business Cards", "slug": "business-cards", "category": "cards",
     "description": "Premium 300gsm cards with matte/gloss lamination.",
     "base_setup_cost": Decimal("150"), "per_sq_inch_rate": Decimal("0.80"),
     "min_qty": 100, "weight_per_unit_kg": Decimal("0.005"), "display_order": 1,
     "sizes": [{"name": '3.5"x2"', "width": Decimal("3.5"), "height": Decimal("2"), "unit": "in"}]},
    {"name": "Flyers & Leaflets", "slug": "flyers-leaflets", "category": "flyers",
     "description": "High-volume A5/A4 flyers on art paper.",
     "base_setup_cost": Decimal("200"), "per_sq_inch_rate": Decimal("0.35"),
     "min_qty": 100, "weight_per_unit_kg": Decimal("0.010"), "display_order": 2,
     "sizes": [{"name": "A5", "width": Decimal("148"), "height": Decimal("210"), "unit": "mm"},
               {"name": "A4", "width": Decimal("210"), "height": Decimal("297"), "unit": "mm"}]},
    {"name": "PVC Banners", "slug": "pvc-banners", "category": "banners",
     "description": "Large-format PVC banners, any custom size in feet.",
     "base_setup_cost": Decimal("100"), "per_sq_inch_rate": Decimal("0.55"),
     "min_qty": 1, "weight_per_unit_kg": Decimal("0.400"), "display_order": 3,
     "sizes": [{"name": "3x2 ft", "width": Decimal("3"), "height": Decimal("2"), "unit": "ft"},
               {"name": "6x3 ft", "width": Decimal("6"), "height": Decimal("3"), "unit": "ft"}]},
    {"name": "Letterheads", "slug": "letterheads", "category": "office",
     "description": "Crisp 80gsm offset letterheads.",
     "base_setup_cost": Decimal("150"), "per_sq_inch_rate": Decimal("0.30"),
     "min_qty": 100, "weight_per_unit_kg": Decimal("0.008"), "display_order": 4,
     "sizes": [{"name": "A4", "width": Decimal("210"), "height": Decimal("297"), "unit": "mm"}]},
    {"name": "Stickers & Labels", "slug": "stickers-labels", "category": "packaging",
     "description": "Die-cut stickers and product labels.",
     "base_setup_cost": Decimal("200"), "per_sq_inch_rate": Decimal("0.90"),
     "min_qty": 100, "weight_per_unit_kg": Decimal("0.004"), "display_order": 5,
     "sizes": [{"name": '2"x2"', "width": Decimal("2"), "height": Decimal("2"), "unit": "in"},
               {"name": '3"x3"', "width": Decimal("3"), "height": Decimal("3"), "unit": "in"}]},
]

PAPERS = [
    {"name": "80gsm Offset", "gsm": "80gsm", "multiplier": Decimal("0.800"), "display_order": 1},
    {"name": "120gsm Art Paper", "gsm": "120gsm", "multiplier": Decimal("1.000"), "display_order": 2},
    {"name": "300gsm Art Card", "gsm": "300gsm", "multiplier": Decimal("1.600"), "display_order": 3},
    {"name": "PVC Banner", "gsm": "13oz", "multiplier": Decimal("1.200"), "display_order": 4},
    {"name": "Acrylic", "gsm": "3mm", "multiplier": Decimal("4.000"), "display_order": 5},
]

FINISHINGS = [
    {"kind": "SIDE", "name": "Single-Sided (4/0)", "price": Decimal("0"), "per_unit": False, "display_order": 1},
    {"kind": "SIDE", "name": "Double-Sided (4/4)", "price": Decimal("2"), "per_unit": True, "display_order": 2},
    {"kind": "LAMINATION", "name": "Glossy Lamination", "price": Decimal("3"), "per_unit": True, "display_order": 1},
    {"kind": "LAMINATION", "name": "Matte Lamination", "price": Decimal("3"), "per_unit": True, "display_order": 2},
    {"kind": "LAMINATION", "name": "Spot UV", "price": Decimal("8"), "per_unit": True, "display_order": 3},
    {"kind": "FINISHING", "name": "Die-Cutting", "price": Decimal("500"), "per_unit": False, "display_order": 1},
    {"kind": "FINISHING", "name": "Creasing", "price": Decimal("1"), "per_unit": True, "display_order": 2},
    {"kind": "FINISHING", "name": "Foil Stamping (Gold)", "price": Decimal("5"), "per_unit": True, "display_order": 3},
    {"kind": "FINISHING", "name": "Foil Stamping (Silver)", "price": Decimal("5"), "per_unit": True, "display_order": 4},
]

SHIPPING = [
    {"zone": "INSIDE_DHAKA_HOME", "courier": "Pathao", "base_fee": Decimal("80"), "per_kg_fee": Decimal("20")},
    {"zone": "INSIDE_DHAKA_HOME", "courier": "Steadfast", "base_fee": Decimal("70"), "per_kg_fee": Decimal("20")},
    {"zone": "HUB_PICKUP", "courier": "Hub Pickup", "base_fee": Decimal("0"), "per_kg_fee": Decimal("0")},
    {"zone": "OUTSIDE_DHAKA", "courier": "Sundarban Courier", "base_fee": Decimal("130"), "per_kg_fee": Decimal("25")},
    {"zone": "OUTSIDE_DHAKA", "courier": "SA Paribahan", "base_fee": Decimal("120"), "per_kg_fee": Decimal("25")},
    {"zone": "OUTSIDE_DHAKA", "courier": "Paperfly", "base_fee": Decimal("140"), "per_kg_fee": Decimal("25")},
]


def seed(apps, schema_editor):
    PressProduct = apps.get_model("printing", "PressProduct")
    PressSizePreset = apps.get_model("printing", "PressSizePreset")
    PaperStock = apps.get_model("printing", "PaperStock")
    FinishingOption = apps.get_model("printing", "FinishingOption")
    PressShippingRate = apps.get_model("printing", "PressShippingRate")
    PressShopConfig = apps.get_model("printing", "PressShopConfig")

    if not PressShopConfig.objects.exists():
        PressShopConfig.objects.create(
            shipping_matrix={"inside_dhaka_home": 80, "hub_pickup": 0, "outside_dhaka": 130, "per_kg": 20},
        )

    for spec in PRODUCTS:
        sizes = spec.pop("sizes")
        product, _ = PressProduct.objects.get_or_create(
            slug=spec["slug"],
            defaults={**spec, "allow_custom_size": True, "is_active": True},
        )
        for order, size in enumerate(sizes):
            PressSizePreset.objects.get_or_create(
                product_id=product.pk, name=size["name"],
                defaults={**size, "display_order": order, "is_active": True},
            )

    for order, spec in enumerate(PAPERS):
        PaperStock.objects.get_or_create(
            name=spec["name"],
            defaults={**spec, "flat_addon_per_unit": Decimal("0"), "is_active": True},
        )

    for spec in FINISHINGS:
        FinishingOption.objects.get_or_create(
            kind=spec["kind"], name=spec["name"],
            defaults={"price": spec["price"], "per_unit": spec["per_unit"],
                      "display_order": spec["display_order"], "is_active": True},
        )

    for spec in SHIPPING:
        PressShippingRate.objects.get_or_create(
            zone=spec["zone"], courier=spec["courier"],
            defaults={"base_fee": spec["base_fee"], "per_kg_fee": spec["per_kg_fee"], "is_active": True},
        )


class Migration(migrations.Migration):

    dependencies = [
        ('printing', '0004_press_engine'),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
