# Seeds the printable garments and print areas the Custom Printing form needs.
#
# Without these the form's "Garment" dropdown renders EMPTY and a customer
# cannot submit a request at all — the models shipped in 0001 with no rows.
#
# Garments mirror the apparel lines shown on the Custom Printing showcase
# page (see frontend .../storefront/pages/printing/catalogue.js), which in
# turn follows the corporate lineup a Bangladeshi merch buyer expects.
#
# `base_price` is deliberately 0 on every row: the owner has not set his blank
# garment costs, and inventing them would quote customers prices he never
# agreed to. 0 means "priced on the proof", which is how the flow already
# works — price is snapshotted onto the request when he approves it. He can
# fill real numbers in the admin at any time without a deploy.
from django.db import migrations

SIZES = ["S", "M", "L", "XL", "XXL"]
COLORS = ["White", "Black", "Navy", "Red", "Green"]

GARMENTS = [
    "Round Neck T-Shirt",
    "Polo T-Shirt",
    "Dye-Sublimation T-Shirt",
    "Dye-Sublimation Polo",
    "Football Jersey",
    "Cricket Jersey",
    "Hoodie",
    "Sweatshirt",
    "Jacket",
    "Formal Shirt",
    "Apron",
    "Cap",
    "Tote Bag",
]

# Flat per-location charges, also 0 for the same reason as base_price.
AREAS = ["Front", "Back", "Left Sleeve", "Right Sleeve", "Chest (small)", "Collar"]


def seed(apps, schema_editor):
    PrintablePreset = apps.get_model("printing", "PrintablePreset")
    PrintArea = apps.get_model("printing", "PrintArea")

    for i, name in enumerate(GARMENTS):
        # get_or_create, not create: this must be safe to re-run and must never
        # clobber prices/colours the owner has since edited in the admin.
        PrintablePreset.objects.get_or_create(
            name=name,
            defaults={
                "display_order": i * 10,
                "available_sizes": SIZES,
                "available_colors": COLORS,
                "is_active": True,
            },
        )

    for i, name in enumerate(AREAS):
        PrintArea.objects.get_or_create(
            name=name, defaults={"display_order": i * 10, "is_active": True},
        )


def unseed(apps, schema_editor):
    # Only remove rows still untouched by the owner (price 0, no linked
    # product) so a reverse migration cannot delete real configuration.
    apps.get_model("printing", "PrintablePreset").objects.filter(
        name__in=GARMENTS, base_price=0, product__isnull=True
    ).delete()
    apps.get_model("printing", "PrintArea").objects.filter(name__in=AREAS, price=0).delete()


class Migration(migrations.Migration):

    dependencies = [("printing", "0001_initial")]

    operations = [migrations.RunPython(seed, unseed)]
