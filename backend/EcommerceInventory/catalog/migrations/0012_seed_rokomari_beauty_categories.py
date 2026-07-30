# Seeds ImportSourceCategory rows mapping rokomari.com's 15 live beauty/health
# subcategories (see 0009_seed_rokomari_source.py's docstring -- verified live
# 2026-07-30 against https://www.rokomari.com/product/category/2355/beauty-health)
# onto the new beauty-health taxonomy branch added to
# seed_store_catalog.TAXONOMY in the same change. Before this branch existed
# there was nowhere honest to map these onto, so 0009 deliberately seeded zero
# rows here -- this migration is what makes them browsable from the admin
# import-tool dropdown instead of requiring an admin to type a raw source path
# by hand.
#
# source_path slugs are our own slugify(name) guess appended to the category
# id -- rokomari's own in-page subcategory links only carry the bare id
# (e.g. "/product/category/2533", no slug segment at all; only the top-level
# beauty-health link happened to carry one). Since browse_candidates() simply
# appends category_path to the site's base_url and fetches it,  an incorrect
# trailing slug is not fatal PROVIDED rokomari's routing keys off the numeric
# id and treats the slug as cosmetic (true of the one page actually inspected
# live). This could not be verified for all 15 pages without triggering 15
# more fetches against the live site; if any of these 404 in practice, only
# this migration's data needs correcting -- the mapping is admin-editable
# from the ImportSourceCategory endpoints either way.
from django.db import migrations

# (rokomari category id, slug, label, our taxonomy leaf slug)
BEAUTY_HEALTH_CATEGORIES = [
    (2533, "hand-sanitizer", "Hand Sanitizer", "beauty-hand-sanitizer"),
    (2618, "perfume", "Perfume", "beauty-perfume"),
    (2619, "body-spray", "Body Spray", "beauty-body-spray"),
    (2620, "air-freshener", "Air Freshener", "beauty-air-freshener"),
    (2621, "adult-diaper", "Adult Diaper", "beauty-adult-diaper"),
    (2622, "shaving-grooming-accessories", "Shaving & Grooming Accessories", "beauty-shaving-grooming"),
    (2623, "talcum-powder", "Talcum Powder", "beauty-talcum-powder"),
    (2843, "personal-care", "Personal Care", "beauty-personal-care"),
    (3161, "medical-supplies", "Medical Supplies", "beauty-medical-supplies"),
    (3222, "makeup", "Makeup", "beauty-makeup"),
    (3863, "herbal-skin-care", "Herbal Skin Care", "beauty-herbal-skin-care"),
    (6281, "nail-care", "Nail Care", "beauty-nail-care"),
    (6947, "beauty-tools", "Beauty Tools", "beauty-tools"),
    (7067, "herbal-hair-care", "Herbal Hair Care", "beauty-herbal-hair-care"),
    (7276, "deodorant", "Deodorant", "beauty-deodorant"),
]


def seed_categories(apps, schema_editor):
    ImportSource = apps.get_model("catalog", "ImportSource")
    ImportSourceCategory = apps.get_model("catalog", "ImportSourceCategory")
    source = ImportSource.objects.filter(slug="rokomari").first()
    if source is None:
        # Defensive only -- 0009 always runs first (explicit dependency
        # below); a missing row here would mean that migration was reverted.
        return
    for order, (cat_id, slug, label, our_slug) in enumerate(BEAUTY_HEALTH_CATEGORIES):
        ImportSourceCategory.objects.get_or_create(
            source=source,
            source_path=f"product/category/{cat_id}/{slug}",
            defaults={"label": label, "our_category_slug": our_slug, "display_order": order},
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0011_products_dosage_form_products_generic_name_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_categories, noop_reverse),
    ]
