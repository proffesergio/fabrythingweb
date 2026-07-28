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
import io
import json
import os

import requests
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from accounts.models import Users
from catalog.models import Categories, Products, ProductVariant

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "seed")
SKU_PREFIX = "FS"  # FS-xxxx: distinct from seed_bd_store's FT-xxxx

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
        """Download -> compress (max 800x800 JPEG q80) -> our storage.

        Never hotlink a partner's image: every URL a fixture supplies gets
        downloaded once, recompressed to an affordable size, and re-uploaded
        to our own storage; only our own URL is ever stored on the product.
        Returns None on any failure so one bad image never sinks the seed.
        """
        from PIL import Image

        from core.storage import save_file
        try:
            r = requests.get(url, timeout=20,
                             headers={"User-Agent": "Mozilla/5.0 (fabrything import)"})
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content)).convert("RGB")
            img.thumbnail((800, 800))
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=80, optimize=True)
            name = os.urandom(12).hex() + ".jpg"
            return save_file(name, buf.getvalue(), "image/jpeg")
        except Exception as e:  # noqa: BLE001 — a bad image must never sink the seed
            self.stdout.write(self.style.WARNING(f"  image skipped ({url}): {e}"))
            return None

    def _next_sku(self, n):
        """Return the first unused ``FS-<n>`` SKU at or after ``n``.

        Deriving the starting point from ``Products.objects.filter(sku__
        startswith=...).count()`` is only ever a *hint*: an admin can rename a
        seeded product's SKU away from the FS- prefix, delete a row, or a
        previous run can leave gaps, all of which desync a stored count from
        the true set of taken numbers. Checking existence at the point of
        assignment (and advancing past any collision) is what actually
        guarantees Products.sku stays unique — the count is just where the
        search starts, not the answer.
        """
        while Products.objects.filter(sku=f"{SKU_PREFIX}-{n}").exists():
            n += 1
        return n

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
                slug = slugify(e["name"])[:250]
                cat = cat_map.get(e["category_path"])
                if cat is None:
                    self.stdout.write(self.style.WARNING(
                        f"  unknown category_path {e['category_path']!r} — skipped {slug}"))
                    continue

                existing = Products.objects.filter(slug=slug).first()
                if existing is not None and not force:
                    continue  # create-only: never touch an admin-editable row

                images = [u for u in (self._import_image(src)
                                     for src in e.get("images", [])[:3]) if u]
                sell = float(e["price"])
                disc = float(e["discount_price"]) if e.get("discount_price") else None
                defaults = {
                    "name": e["name"],
                    "description": e.get("description") or e["name"],
                    "specifications": e.get("specifications") or {},
                    "brand": e.get("brand") or "",
                    "gender": e.get("gender") or "UNISEX",
                    "material": e.get("material") or "",
                    "available_sizes": e.get("sizes") or [],
                    "image": images,
                    "initial_buying_price": round(sell * 0.85),  # dealer-price placeholder
                    "initial_selling_price": sell,
                    "discount_price": disc,
                    "source_url": e.get("source_url") or "",
                    "source_price": sell if e.get("source_url") else None,
                    "price_synced_at": timezone.now() if e.get("source_url") else None,
                    "category_id": cat,
                    "status": "ACTIVE",
                    "domain_user_id": owner,
                    "added_by_user_id": owner,
                    "seo_title": f"{e['name']} - Fabrything",
                    "seo_description": (e.get("description") or e["name"])[:160],
                }

                if existing is not None:
                    # --force-update: refresh the admin-visible fields, but
                    # never regenerate the SKU here — it's an identity
                    # assigned once at creation, not fixture data, and other
                    # records (POs, invoices) may reference it. Reassigning it
                    # on every force run would needlessly churn that identity.
                    for field, value in defaults.items():
                        setattr(existing, field, value)
                    existing.save()
                    product = existing
                else:
                    sku_n = self._next_sku(sku_n)
                    product = Products.objects.create(
                        slug=slug, sku=f"{SKU_PREFIX}-{sku_n}", **defaults)
                    sku_n += 1
                    created += 1

                sizes = e.get("sizes") or [""]
                for size in sizes:
                    ProductVariant.objects.get_or_create(
                        product=product, size=size, color="",
                        defaults={"sku": f"{product.sku}-{size or 'DEF'}",
                                  "price": disc or sell, "stock_quantity": 25})
        self.stdout.write(self.style.SUCCESS(f"Products: {created} created."))
