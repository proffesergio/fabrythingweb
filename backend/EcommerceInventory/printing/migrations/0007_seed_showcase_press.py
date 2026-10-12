# Seed ColorLifePrint-style showcase designs (typographic tiles until the
# owner uploads real design files from the admin). Idempotent.
from decimal import Decimal

from django.db import migrations


ITEMS = [
    {"name": "Foil Business Cards", "category": "business-cards", "badge": "HOT",
     "price_bdt": Decimal("450"), "is_top_pick": True, "product_slug": "business-cards",
     "note": "Gold/silver foil on 300gsm art card", "display_order": 1},
    {"name": "Spot UV Business Cards", "category": "business-cards", "badge": "HOT",
     "price_bdt": Decimal("380"), "is_top_pick": True, "product_slug": "business-cards",
     "note": "Raised gloss highlights on matte", "display_order": 2},
    {"name": "Velvet Laminated Business Cards", "category": "business-cards", "badge": "HOT",
     "price_bdt": Decimal("320"), "is_top_pick": True, "product_slug": "business-cards",
     "note": "Soft-touch velvet lamination", "display_order": 3},
    {"name": "Transparent Business Cards", "category": "business-cards", "badge": "HOT",
     "price_bdt": Decimal("350"), "is_top_pick": True, "product_slug": "business-cards",
     "note": "Frosted PVC, white ink", "display_order": 4},
    {"name": "Brochures Printing", "category": "brochures-catalogues", "badge": "HOT",
     "price_bdt": Decimal("1200"), "is_top_pick": True, "product_slug": "flyers-leaflets",
     "note": "Tri-fold and bi-fold, A4/A5", "display_order": 5},
    {"name": "Flyers & Leaflets", "category": "flyers-brochures", "badge": "NEW",
     "price_bdt": Decimal("800"), "is_top_pick": True, "product_slug": "flyers-leaflets",
     "note": "High-volume 120gsm art paper", "display_order": 6},
    {"name": "PVC Banners", "category": "large-format", "badge": "OFFER",
     "price_bdt": Decimal("150"), "is_top_pick": True, "product_slug": "pvc-banners",
     "note": "Any custom size in feet", "display_order": 7},
    {"name": "Stickers & Labels", "category": "stickers-labels", "badge": "NEW",
     "price_bdt": Decimal("500"), "is_top_pick": True, "product_slug": "stickers-labels",
     "note": "Die-cut, waterproof options", "display_order": 8},
    {"name": "Letterheads", "category": "letterheads", "badge": "",
     "price_bdt": Decimal("600"), "is_top_pick": True, "product_slug": "letterheads",
     "note": "Crisp 80gsm offset", "display_order": 9},
    {"name": "Corporate Stationery Set", "category": "corporate-stationery", "badge": "NEW",
     "price_bdt": Decimal("2500"), "is_top_pick": False, "product_slug": None,
     "note": "Letterhead + envelope + visiting cards", "display_order": 10},
    {"name": "Box & Packaging", "category": "box-packaging", "badge": "HOT",
     "price_bdt": Decimal("1800"), "is_top_pick": False, "product_slug": None,
     "note": "Custom rigid and corrugated boxes", "display_order": 11},
    {"name": "Posters", "category": "posters", "badge": "OFFER",
     "price_bdt": Decimal("250"), "is_top_pick": False, "product_slug": None,
     "note": "A3/A2 art paper posters", "display_order": 12},
]


def seed(apps, schema_editor):
    PrintShowcaseItem = apps.get_model("printing", "PrintShowcaseItem")
    PressProduct = apps.get_model("printing", "PressProduct")
    products = {p.slug: p.pk for p in PressProduct.objects.all()}
    for spec in ITEMS:
        product_pk = products.get(spec.pop("product_slug", None))
        PrintShowcaseItem.objects.get_or_create(
            name=spec["name"], category=spec["category"],
            defaults={**spec, "press_product_id": product_pk, "is_active": True},
        )


class Migration(migrations.Migration):

    dependencies = [
        ('printing', '0006_showcase_press_fields'),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
