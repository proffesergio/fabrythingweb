# Turns arogga.com from the disabled placeholder seeded by 0008 into a working
# import source.
#
# 0008's note said "www.arogga.com is client-rendered (the search page has zero
# product links and zero prices in the raw HTML)". Re-verified 2026-08-07
# against live pages: product AND category pages both server-render schema.org
# JSON-LD carrying name, brand, image, price and availability. A category page
# nests a full ItemList of Product entries under CollectionPage.mainEntity, so
# one request yields 30 complete candidates. See catalog/test_fixtures/arogga_*
# (real captured payloads) and the `arogga` adapter in catalog/scrape_parsers.py.
#
# The search branch stays unsupported on purpose: arogga.com/robots.txt
# disallows /search?, so this source browses by category only.
#
# sets_source_url stays False. That field enrols a source in
# catalog.services_price_sync.sync_source_prices, which is for reseller-
# permission partners only (potakait, canvasit). Arogga is a price reference,
# not a partner — flip this only if a reseller agreement is actually in hand.
from django.db import migrations

# (source_path, label, our_category_slug) — paths taken from arogga.com's own
# sitemap, so the ids are real rather than guessed.
AROGGA_CATEGORIES = [
    ("category/medicine/6322/medicine", "Medicine", "health-medicine"),
    ("category/medicine/6323/antimicrobial", "Antimicrobial", "health-medicine"),
    ("category/healthcare/5987/healthcare", "Healthcare", "health-healthcare"),
    ("category/healthcare/6099/thermometer", "Thermometers", "health-healthcare"),
    ("category/healthcare/6118/blood-pressure-monitors-and-accessories",
     "Blood Pressure Monitors", "health-healthcare"),
    ("category/supplement/5989/supplement", "Supplements", "health-supplement"),
    ("category/supplement/5990/multibiotin-and-collagen", "Multibiotin & Collagen", "health-supplement"),
    ("category/supplement/5991/women-s-multivitamins", "Women's Multivitamins", "health-supplement"),
    ("category/baby-mom-care/6054/baby-cereals", "Baby Cereals", "health-baby-mom-care"),
    ("category/baby-mom-care/6285/baby-powder", "Baby Powder", "health-baby-mom-care"),
    ("category/baby-mom-care/6286/baby-lotion", "Baby Lotion", "health-baby-mom-care"),
    ("category/herbal/6174/herbal", "Herbal", "health-herbal"),
    ("category/food-and-nutrition/7276/food-and-nutrition", "Food & Nutrition", "health-food-nutrition"),
    ("category/food-and-nutrition/7277/snacks-beverages", "Snacks & Beverages", "health-food-nutrition"),
    ("category/sexual-wellness/6304/sexual-wellness", "Sexual Wellness", "health-sexual-wellness"),
    ("category/sexual-wellness/6308/condoms", "Condoms", "health-sexual-wellness"),
    ("category/home-care/7043/hand-washes-sanitizers", "Hand Wash & Sanitisers", "health-home-care"),
    ("category/home-care/6169/air-fresheners", "Air Fresheners", "health-home-care"),
]

NOTES = (
    "Enabled 2026-08-07. Adapter reads schema.org JSON-LD, which arogga.com "
    "server-renders on both product and category pages -- 0008's "
    "'client-rendered, zero prices' note was measured against the search page "
    "and no longer describes the product/category pages. Browse only: "
    "robots.txt disallows /search?. sets_source_url stays False (price "
    "reference, not a reseller partner) so sync_source_prices leaves these "
    "products alone. Medicines flagged 'requires a prescription' on the source "
    "page import with Products.requires_prescription=True and stay blocked at "
    "checkout until StoreConfiguration.rx_sales_enabled is on (DGDA licence)."
)


def enable_arogga(apps, schema_editor):
    ImportSource = apps.get_model("catalog", "ImportSource")
    ImportSourceCategory = apps.get_model("catalog", "ImportSourceCategory")

    source = ImportSource.objects.filter(slug="arogga").first()
    if source is None:
        # 0008 seeds it; recreate rather than fail if an operator removed it.
        source = ImportSource(name="Arogga.com", slug="arogga",
                              base_url="https://www.arogga.com/")
    source.base_url = "https://www.arogga.com/"
    source.adapter_key = "arogga"
    source.supports_search = False
    source.is_enabled = True
    source.sets_source_url = False
    source.notes = NOTES
    source.save()

    for order, (path, label, our_slug) in enumerate(AROGGA_CATEGORIES):
        ImportSourceCategory.objects.update_or_create(
            source=source, source_path=path,
            defaults={"label": label, "our_category_slug": our_slug, "display_order": order},
        )


def disable_arogga(apps, schema_editor):
    """Back out to 0008's disabled-with-reason shape."""
    ImportSource = apps.get_model("catalog", "ImportSource")
    ImportSourceCategory = apps.get_model("catalog", "ImportSourceCategory")
    source = ImportSource.objects.filter(slug="arogga").first()
    if source is None:
        return
    ImportSourceCategory.objects.filter(source=source).delete()
    source.adapter_key = ""
    source.is_enabled = False
    source.save()


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0012_seed_rokomari_beauty_categories"),
    ]

    operations = [
        migrations.RunPython(enable_arogga, disable_arogga),
    ]
