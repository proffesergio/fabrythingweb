# Seeds rokomari.com as an ImportSource -- a reference source (owner has no
# reseller agreement with them), NOT a partner like potakait/canvasit, so
# sets_source_url=False: these imports must never enter
# catalog.services_price_sync.sync_source_prices's re-pricing loop.
#
# Category mappings: verified live 2026-07-30 that the beauty/health category
# page (https://www.rokomari.com/product/category/2355/beauty-health) lists
# 15 real subcategories: Hand Sanitizer (2533), Perfume (2618), Body Spray
# (2619), Air Freshener (2620), Adult Diaper (2621), Shaving & Grooming
# Accessories (2622), Talcum Powder (2623), Personal Care (2843), Medical
# Supplies (3161), Makeup (3222), Herbal Skin Care (3863), Nail Care (6281),
# Beauty Tools (6947), Herbal Hair Care (7067), Deodorant (7276).
#
# seed_store_catalog.TAXONOMY (catalog/management/commands/seed_store_catalog.py)
# currently has exactly four top-level branches: fashion, phones, computers,
# gadgets -- there is no beauty/health/personal-care/pharmacy branch at all.
# None of the 15 subcategories above has an honest home in any of those four
# trees (a "Herbal Hair Care" or "Adult Diaper" filed under "gadgets" would be
# actively misleading, not just imprecise). Per the task brief: report this
# rather than invent a new taxonomy node here. So this migration seeds ZERO
# ImportSourceCategory rows -- an admin can still browse/import by pasting a
# raw source category path (e.g. "product/category/2843/personal-care") into
# the import tool's free-text category field, same as any source; only the
# admin-panel dropdown convenience is missing until a beauty/health taxonomy
# branch exists to seed these into.
from django.db import migrations


def seed_rokomari(apps, schema_editor):
    ImportSource = apps.get_model("catalog", "ImportSource")
    ImportSource.objects.create(
        name="Rokomari.com", slug="rokomari", base_url="https://www.rokomari.com/",
        adapter_key="rokomari", supports_search=True, is_enabled=True,
        sets_source_url=False,
        notes="Reference source, not a reseller partner -- source_url must stay off so "
              "the price-sync job never re-prices these. Free-text search verified live "
              "at /search?term=<q>&search_type=ALL (search_type=products, the more "
              "obvious-looking guess, 500s). No beauty/health branch exists yet in "
              "seed_store_catalog.TAXONOMY, so no ImportSourceCategory rows are seeded "
              "here -- see this migration's module docstring for the 15 subcategories "
              "that have no taxonomy home to map onto.",
    )


def noop_reverse(apps, schema_editor):
    # Same rationale as 0008_seed_import_sources.noop_reverse: by the time
    # anyone reverses this, the row may already have ImportRun history or
    # imported products pointing at it.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0008_seed_import_sources"),
    ]

    operations = [
        migrations.RunPython(seed_rokomari, noop_reverse),
    ]
