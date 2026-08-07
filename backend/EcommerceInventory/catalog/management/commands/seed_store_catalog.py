"""Seed the expanded multi-vertical store taxonomy (and, with fixtures,
real products scraped from partner/reference sites).

    python manage.py seed_store_catalog                    # categories + all fixtures
    python manage.py seed_store_catalog --categories-only
    python manage.py seed_store_catalog --fixture potakait # one fixture
    python manage.py seed_store_catalog --force-update     # overwrite existing rows

Create-only by slug (the seed_bancharampur lesson): re-runs never clobber
admin edits unless --force-update is passed. Legacy top-level
mens-fashion/womens-fashion (from seed_bd_store) are adopted into the new
Fashion tree; that re-parent is a one-time structural migration (identified by
the row still being top-level) and always applies once. After adoption, the
row is treated like any other admin-editable category.
"""
import json
import os

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from accounts.models import Users
from catalog.models import Categories, Products
from catalog.services_import import SKU_PREFIX, import_image, seed_product_entry

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "seed")

# (slug, name, description, children)
TAXONOMY = [
    ("fashion", "Fashion", "Clothing for men, women & kids — everyday to festive.", [
        ("fashion-men", "Men", "T-shirts, polos, shirts, panjabi & more.", [
            ("men-tshirts", "T-shirts", "Half & full sleeve tees.", []),
            ("men-polos", "Polos", "Pique & jacquard polo shirts.", []),
            ("men-shirts", "Shirts", "Formal & casual shirts.", []),
            ("men-panjabi", "Panjabi", "Eid & festive panjabi.", []),
            ("men-hoodies", "Hoodies & Sweatshirts", "Fleece & terry warmers.", []),
            ("men-jackets", "Jackets", "Denim, bomber & windbreakers.", []),
            ("men-bottoms", "Joggers & Trousers", "Joggers, chinos & trousers.", []),
            ("men-shorts", "Shorts", "Cotton & sport shorts.", []),
        ]),
        ("fashion-women", "Women", "Kurti, tops, salwar kameez & co-ords.", [
            ("women-kurti-tops", "Kurti & Tops", "Kurtis, tops & tunics.", []),
            ("women-tshirts", "T-shirts", "Relaxed & fitted tees.", []),
            ("women-salwar-kameez", "Salwar Kameez", "2pc & 3pc sets.", []),
            ("women-coords", "Co-ords", "Matching two-piece sets.", []),
            ("women-bottoms", "Leggings & Palazzo", "Leggings, palazzo & comfy trousers.", []),
        ]),
        ("fashion-kids", "Kids", "Boys' & girls' clothing.", [
            ("kids-boys", "Boys", "Tees, polos, shorts & sets.", []),
            ("kids-girls", "Girls", "Frocks, tees, skirts & sets.", []),
        ]),
    ]),
    ("phones", "Phones", "Smartphones & tablets from every major brand.", [
        ("phones-smartphones", "Smartphones", "Android & iPhone.", []),
        ("phones-tablets", "Tablets", "iPad & Android tablets.", []),
    ]),
    ("computers", "Computers", "Laptops, desktops, components & office gear.", [
        ("computers-laptops", "Laptops", "Ultrabooks, gaming & MacBooks.", []),
        ("computers-desktops", "Desktops & All-in-Ones", "Gaming PCs, brand PCs & AIOs.", []),
        ("computers-monitors", "Monitors", "Office, gaming & professional monitors.", []),
        ("computers-components", "Components", "CPU, RAM, SSD, GPU, PSU, casing.", []),
        ("computers-keyboards-mice", "Keyboards & Mice", "Mechanical keyboards, mice & combos.", []),
        ("computers-printers-office", "Printers & Office", "Printers, scanners & POS.", []),
        ("computers-networking", "Networking", "Routers, adapters & switches.", []),
    ]),
    ("gadgets", "Gadgets", "Wearables, audio & smart devices.", [
        ("gadgets-smart-watches", "Smart Watches", "Smart & fitness watches.", []),
        ("gadgets-earbuds", "Earbuds & Headphones", "TWS earbuds & headphones.", []),
        ("gadgets-speakers", "Speakers & Audio", "Bluetooth speakers & soundbars.", []),
        ("gadgets-power", "Power Banks & Chargers", "Power banks, chargers & cables.", []),
        ("gadgets-cases", "Cases & Protection", "Phone cases & screen protectors.", []),
        ("gadgets-cameras", "Cameras & Drones", "Action cams & drones.", []),
        ("gadgets-smart-home", "Smart Home", "Smart bulbs, plugs & security cams.", []),
    ]),
    # Added for the Rokomari affiliate automation feature: the 15 live
    # rokomari.com beauty/health subcategories (see the 0009 migration's
    # seed_rokomari_source docstring) had no honest home in any of the four
    # branches above and were seeding zero ImportSourceCategory rows as a
    # result. See catalog/migrations/0012_seed_rokomari_beauty_categories.py
    # for the mapping this branch exists to receive.
    ("beauty-health", "Beauty & Health", "Personal care, cosmetics & wellness essentials.", [
        ("beauty-hand-sanitizer", "Hand Sanitizer", "Hand sanitizers & antiseptics.", []),
        ("beauty-perfume", "Perfume", "Perfumes & attars.", []),
        ("beauty-body-spray", "Body Spray", "Deodorant body sprays.", []),
        ("beauty-air-freshener", "Air Freshener", "Room & car air fresheners.", []),
        ("beauty-adult-diaper", "Adult Diaper", "Adult diapers & incontinence care.", []),
        ("beauty-shaving-grooming", "Shaving & Grooming", "Razors, trimmers & grooming accessories.", []),
        ("beauty-talcum-powder", "Talcum Powder", "Talcum & body powders.", []),
        ("beauty-personal-care", "Personal Care", "Everyday personal-care essentials.", []),
        ("beauty-medical-supplies", "Medical Supplies", "Basic medical & first-aid supplies.", []),
        ("beauty-makeup", "Makeup", "Cosmetics & makeup.", []),
        ("beauty-herbal-skin-care", "Herbal Skin Care", "Herbal & natural skincare.", []),
        ("beauty-nail-care", "Nail Care", "Nail polish & nail-care tools.", []),
        ("beauty-tools", "Beauty Tools", "Brushes, mirrors & beauty tools.", []),
        ("beauty-herbal-hair-care", "Herbal Hair Care", "Herbal & natural hair care.", []),
        ("beauty-deodorant", "Deodorant", "Deodorants & antiperspirants.", []),
    ]),
    # Receives the arogga.com mapping (see
    # catalog/migrations/0013_enable_arogga_import_source.py). Kept separate
    # from `beauty-health`, which is cosmetics/personal care: these are
    # pharmacy lines, and `health-medicine` in particular holds items that may
    # carry Products.requires_prescription and are therefore blocked at
    # checkout until StoreConfiguration.rx_sales_enabled is turned on.
    ("health", "Health & Pharmacy", "Medicines, supplements and healthcare essentials.", [
        ("health-medicine", "Medicine", "Prescription and over-the-counter medicines.", []),
        ("health-healthcare", "Healthcare Devices", "Thermometers, BP monitors & medical devices.", []),
        ("health-supplement", "Supplements", "Vitamins, minerals & nutritional supplements.", []),
        ("health-baby-mom-care", "Baby & Mom Care", "Baby and maternal care essentials.", []),
        ("health-herbal", "Herbal", "Herbal and ayurvedic remedies.", []),
        ("health-food-nutrition", "Food & Nutrition", "Nutritional food, drinks & snacks.", []),
        ("health-sexual-wellness", "Sexual Wellness", "Sexual wellness and family planning.", []),
        ("health-home-care", "Home Care", "Sanitisers, cleaners & home hygiene.", []),
    ]),
]

# Legacy top-level slugs from seed_bd_store, adopted into the new tree in place
# of the taxonomy node they duplicate. Structural: applied even without --force-update.
ADOPT_LEGACY = {"mens-fashion": "fashion-men", "womens-fashion": "fashion-women"}


def _owner():
    return (Users.objects.filter(role="Super Admin").order_by("id").first()
            or Users.objects.filter(role="Admin").order_by("id").first()
            or Users.objects.order_by("id").first())


class Command(BaseCommand):
    help = "Seed the expanded store taxonomy and fixture products (create-only)."

    def add_arguments(self, parser):
        parser.add_argument("--categories-only", action="store_true")
        parser.add_argument("--fixture", default=None,
                            help="Seed only this fixture (basename without .json).")
        parser.add_argument("--force-update", action="store_true",
                            help="Overwrite existing seeded rows (clobbers admin edits).")

    @transaction.atomic
    def handle(self, *args, **options):
        owner = _owner()
        if owner is None:
            self.stdout.write(self.style.ERROR("No user to own seeded rows; aborting."))
            return
        cat_map = self._seed_categories(owner, force=options["force_update"])
        self.stdout.write(self.style.SUCCESS(f"Categories ready: {len(cat_map)} in tree."))
        if not options["categories_only"]:
            self._seed_products(owner, cat_map, only=options["fixture"],
                                force=options["force_update"])  # Task 7

    def _seed_categories(self, owner, force=False):
        # legacy taxonomy-slug -> adopted Categories row, keyed by the slug it replaces
        adopted = {}
        for legacy_slug, taxonomy_slug in ADOPT_LEGACY.items():
            legacy = Categories.objects.filter(slug=legacy_slug).first()
            if legacy is not None:
                adopted[taxonomy_slug] = legacy

        cat_map, order = {}, 0

        def walk(nodes, parent):
            nonlocal order
            for slug, name, desc, children in nodes:
                order += 10
                if slug in adopted:
                    cat = adopted[slug]
                    # An unadopted legacy category is still top-level (no parent
                    # yet) — that marks it as pending its one-time migration into
                    # the new tree, which is always safe to perform. Once it has
                    # a parent, adoption already happened; any later difference
                    # (e.g. a renamed "Men" -> "Menswear") is an admin edit, not
                    # a pending migration, so leave it alone unless --force-update
                    # explicitly asks to resync it.
                    if cat.parent_id_id is None:
                        cat.parent_id = parent
                        cat.name = name
                        cat.save()
                    elif force:
                        cat.parent_id = parent
                        cat.name = name
                        cat.description = desc
                        cat.save()
                else:
                    cat, created = Categories.objects.get_or_create(
                        slug=slug,
                        defaults={"name": name, "description": desc,
                                  "display_order": order,
                                  "domain_user_id": owner, "added_by_user_id": owner})
                    if not created and force:
                        cat.name, cat.description = name, desc
                        cat.parent_id = parent
                        cat.save()
                    elif created and parent is not None:
                        cat.parent_id = parent
                        cat.save()
                cat_map[slug] = cat
                walk(children, cat)

        walk(TAXONOMY, None)
        return cat_map

    def _import_image(self, url):
        """Download -> compress (max 800x800 JPEG q80) -> our storage. Thin
        wrapper over catalog.services_import.import_image that logs a
        skipped-image warning the way this command always has."""
        def on_error(u, e):
            self.stdout.write(self.style.WARNING(f"  image skipped ({u}): {e}"))
        return import_image(url, on_error=on_error)

    def _seed_products(self, owner, cat_map, only=None, force=False):
        files = sorted(f for f in os.listdir(FIXTURE_DIR) if f.endswith(".json"))
        if only:
            files = [f for f in files if f == f"{only}.json"]
        sku_n = 1000 + Products.objects.filter(sku__startswith=SKU_PREFIX).count()
        created = 0
        for fname in files:
            with open(os.path.join(FIXTURE_DIR, fname), encoding="utf-8") as fh:
                entries = json.load(fh)
            self.stdout.write(f"{fname}: {len(entries)} entries")
            for e in entries:
                cat = cat_map.get(e["category_path"])
                if cat is None:
                    self.stdout.write(self.style.WARNING(
                        f"  unknown category_path {e['category_path']!r} — skipped "
                        f"{slugify(e['name'])[:250]}"))
                    continue

                result = seed_product_entry(
                    e, cat, owner, force=force, import_image_fn=self._import_image,
                    sku_hint=sku_n)
                if result["status"] == "skipped_invalid":
                    self.stdout.write(self.style.WARNING(
                        f"  skipped {result['slug'] or e.get('name')}: {result['reason']}"))
                    continue
                if result["status"] == "created":
                    created += 1
                    sku_n = result["sku_n_used"] + 1
        self.stdout.write(self.style.SUCCESS(f"Products: {created} created."))
