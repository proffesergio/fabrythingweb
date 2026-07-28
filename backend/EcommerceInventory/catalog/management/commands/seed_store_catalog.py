"""Seed the expanded multi-vertical store taxonomy (and, with fixtures,
real products scraped from partner/reference sites).

    python manage.py seed_store_catalog                    # categories + all fixtures
    python manage.py seed_store_catalog --categories-only
    python manage.py seed_store_catalog --fixture potakait # one fixture
    python manage.py seed_store_catalog --force-update     # overwrite existing rows

Create-only by slug (the seed_bancharampur lesson): re-runs never clobber
admin edits unless --force-update is passed. Legacy top-level
mens-fashion/womens-fashion (from seed_bd_store) are adopted into the new
Fashion tree; that re-parent is structural and always applies.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Users
from catalog.models import Categories

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
                    if cat.parent_id_id != (parent.id if parent else None) or cat.name != name:
                        cat.parent_id = parent
                        cat.name = name
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

    def _seed_products(self, owner, cat_map, only=None, force=False):
        self.stdout.write("No product fixtures wired yet (Task 7).")
