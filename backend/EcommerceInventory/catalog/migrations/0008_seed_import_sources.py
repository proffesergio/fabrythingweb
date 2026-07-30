# Seeds the ImportSource/ImportSourceCategory rows that used to live as
# hardcoded dicts in catalog.services_scrape_import (OPENCART_CATEGORY_PATHS,
# FABRILIFE_CATEGORY_PATHS, SOURCE_SEARCH_SUPPORTED) mirrored again in
# frontend/.../ImportProducts.js's FALLBACK_CATEGORIES. Every path/mapping
# below is copied verbatim from those measured-working values so this
# migration is a pure schema move, not a re-verification -- see
# catalog/services_scrape_import.py's pre-refactor history for the
# "VERIFIED against the live sites" provenance notes on each path.
from django.db import migrations

# (source_path, label, our_category_slug)
POTAKAIT_CATEGORIES = [
    ("laptops", "Laptops", "computers-laptops"),
    ("gaming-pc", "Gaming PCs", "computers-desktops"),
    ("monitors", "Monitors", "computers-monitors"),
    ("processors", "Processors", "computers-components"),
    ("keyboards", "Keyboards", "computers-keyboards-mice"),
    ("printers", "Printers", "computers-printers-office"),
    ("router", "Routers", "computers-networking"),
    ("earbuds", "Earbuds", "gadgets-earbuds"),
    ("headphones", "Headphones", "gadgets-earbuds"),
    ("speaker-and-home-theater", "Speakers & Home Theater", "gadgets-speakers"),
    ("power-bank", "Power Banks", "gadgets-power"),
    ("smart-watches", "Smart Watches", "gadgets-smart-watches"),
    ("action-camera", "Action Cameras", "gadgets-cameras"),
    ("mobile-phone-accessories", "Phone Accessories", "gadgets-cases"),
    ("tablet-pc", "Tablets", "phones-tablets"),
    ("gadgets", "Gadgets (all)", "gadgets"),
]

CANVASIT_CATEGORIES = [
    ("laptop", "Laptops", "computers-laptops"),
    ("desktop-pc", "Desktops", "computers-desktops"),
    ("monitor", "Monitors", "computers-monitors"),
    ("processor", "Processors", "computers-components"),
    ("keyboard", "Keyboards", "computers-keyboards-mice"),
    ("printer", "Printers", "computers-printers-office"),
    ("router", "Routers", "computers-networking"),
    ("earbuds", "Earbuds", "gadgets-earbuds"),
    ("headphone", "Headphones", "gadgets-earbuds"),
    ("speaker", "Speakers", "gadgets-speakers"),
    ("power-bank", "Power Banks", "gadgets-power"),
    ("smart-watch", "Smart Watches", "gadgets-smart-watches"),
    ("action-camera", "Action Cameras", "gadgets-cameras"),
    ("drones", "Drones", "gadgets-cameras"),
    ("mobile-phone-accessories", "Phone Accessories", "gadgets-cases"),
    ("phone-tablet", "Phones & Tablets", "phones-tablets"),
    ("gadget", "Gadgets (all)", "gadgets"),
]


def seed_sources(apps, schema_editor):
    ImportSource = apps.get_model("catalog", "ImportSource")
    ImportSourceCategory = apps.get_model("catalog", "ImportSourceCategory")

    def create_source(**kwargs):
        return ImportSource.objects.create(**kwargs)

    def create_categories(source, rows):
        for order, (path, label, our_slug) in enumerate(rows):
            ImportSourceCategory.objects.create(
                source=source, source_path=path, label=label,
                our_category_slug=our_slug, display_order=order,
            )

    potakait = create_source(
        name="Potakait.com", slug="potakait", base_url="https://potakait.com/",
        adapter_key="opencart", supports_search=False, is_enabled=True,
        sets_source_url=True,
        notes="Reseller-permission partner. No reachable search endpoint was found "
              "live (every plausible search route 404s) -- browse by category only.",
    )
    create_categories(potakait, POTAKAIT_CATEGORIES)

    canvasit = create_source(
        name="Canvasit.com.bd", slug="canvasit", base_url="https://canvasit.com.bd/",
        adapter_key="opencart", supports_search=True, is_enabled=True,
        sets_source_url=True,
        notes="Reseller-permission partner. Classic OpenCart search route works "
              "(verified live).",
    )
    create_categories(canvasit, CANVASIT_CATEGORIES)

    # Fabrilife's category paths carry an extra `cats` facet list (the site's
    # own Algolia facet names) that ImportSourceCategory has no column for --
    # that mapping lives in catalog.services_scrape_import's
    # _FABRILIFE_CATS_BY_PATH constant, not the DB, since it's an adapter
    # implementation detail (which Algolia facet string to send) rather than
    # admin-editable config. Seeding the (path, label, our_category_slug) rows
    # here still gives the admin panel a real dropdown; the adapter resolves
    # the facet filter itself from the path.
    fabrilife = create_source(
        name="Fabrilife.com", slug="fabrilife", base_url="https://fabrilife.com/",
        adapter_key="fabrilife", supports_search=True, is_enabled=True,
        sets_source_url=False,
        notes="Not a reseller partner -- source_url must stay off so the price-sync "
              "job never re-prices these.",
    )
    create_categories(fabrilife, [
        ("men-tshirts", "Men's T-shirts", "men-tshirts"),
        ("men-polos", "Men's Polos", "men-polos"),
        ("men-panjabi", "Men's Panjabi", "men-panjabi"),
        ("men-hoodies", "Men's Hoodies", "men-hoodies"),
        ("women-kurti-tops", "Women's Kurti & Tops", "women-kurti-tops"),
        ("women-tshirts", "Women's T-shirts", "women-tshirts"),
        ("kids-boys", "Boys", "kids-boys"),
        ("kids-girls", "Girls", "kids-girls"),
    ])

    create_source(
        name="Arogga.com", slug="arogga", base_url="https://www.arogga.com/",
        adapter_key="", supports_search=False, is_enabled=False,
        sets_source_url=False,
        notes="No working adapter exists yet -- out of scope pending SP3. "
              "www.arogga.com is client-rendered (the search page has zero product "
              "links and zero prices in the raw HTML); api.arogga.com answers a bare "
              "'Welcome to the Arogga nAPI' at its root and every guessed product/"
              "search path 404s or 403s, with no product/search API path visible in "
              "its first JS chunks either. Do not scrape or guess an API for this "
              "source -- enable it only once a real adapter has been verified "
              "against a working endpoint.",
    )


def noop_reverse(apps, schema_editor):
    # Deliberately not deleting the seeded rows on reverse: they may already
    # have ImportRun history or product imports pointing at them by the time
    # anyone reverses this, and this migration's only job was to seed
    # baseline config, not to own its lifecycle after that.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0007_importsource_importrun_importsourcecategory_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_sources, noop_reverse),
    ]
