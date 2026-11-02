# Fabrilife sports category mappings.
#
# The Fabrilife facet strings below were read off their live Algolia index on
# 2026-08-08 with a `facets: ["cats"]` query. A wrong facet is not an error —
# Algolia returns zero hits — so it would present as a permanently empty
# category. They are recorded here verbatim rather than paraphrased.
from django.db import migrations

# (source_path, label, our_category_slug) — source_path must match a key in
# catalog.services_scrape_import._FABRILIFE_CATS_BY_PATH or the browse resolves
# to no facet filter and returns the whole catalogue.
FABRILIFE_SPORTS = [
    ("sports-all", "Sports (all)", "sports"),
    ("sports-jersey", "Football Jerseys", "sports-jersey"),
    ("sports-tshirts", "Sports T-shirts", "sports-tshirts"),
    ("sports-shorts", "Sports Shorts", "sports-shorts"),
    ("sports-trousers", "Sports Trousers", "sports-trousers"),
    ("sports-accessories", "Sports Socks & Accessories", "sports-accessories"),
]

def seed(apps, schema_editor):
    ImportSource = apps.get_model("catalog", "ImportSource")
    ImportSourceCategory = apps.get_model("catalog", "ImportSourceCategory")

    fabrilife = ImportSource.objects.filter(slug="fabrilife").first()
    if fabrilife:
        # Existing rows start at display_order 0; append after them.
        start = ImportSourceCategory.objects.filter(source=fabrilife).count()
        for i, (path, label, our_slug) in enumerate(FABRILIFE_SPORTS):
            ImportSourceCategory.objects.update_or_create(
                source=fabrilife, source_path=path,
                defaults={"label": label, "our_category_slug": our_slug,
                          "display_order": start + i},
            )



def unseed(apps, schema_editor):
    ImportSource = apps.get_model("catalog", "ImportSource")
    ImportSourceCategory = apps.get_model("catalog", "ImportSourceCategory")
    fabrilife = ImportSource.objects.filter(slug="fabrilife").first()
    if fabrilife:
        ImportSourceCategory.objects.filter(
            source=fabrilife, source_path__in=[p for p, _, _ in FABRILIFE_SPORTS]
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0014_alter_importsource_adapter_key"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
