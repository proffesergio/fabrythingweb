"""Remove the dummy demo catalog seeded by `seed_bd_store` (~60 fake products
with loremflickr.com placeholder images across 8 categories) now that the
real catalog (Fabrilife fashion + the two partner computer stores) is live.

`loremflickr.com` in the product's `image` list is the reliable marker --
it's the literal placeholder host `seed_bd_store.img()` builds every URL
from, and it can never appear on a real product's image. The `FT-` SKU
prefix `seed_bd_store` also stamps on every demo product is corroborating
evidence only (report it, don't gate on it): an admin can rename a SKU away
from that prefix without the product stopping being demo data, and nothing
stops a future real product from legitimately starting with "FT-".

Deleting a product that a real order references would corrupt order
history, so that is refused outright rather than made a flag: any demo
product with a variant an OrderItem points at is skipped and printed with
the reason, never deleted.

After products are removed, categories that are left with no products and no
children are removed too -- but only categories that came from the demo seed
(`seed_bd_store.CATEGORIES`). A TAXONOMY category from `seed_store_catalog`
(Fashion/Phones/Computers/Gadgets and everything under them) is never
touched even while empty, because Phones and Gadgets genuinely have no real
products yet and emptiness there is not a signal of demo data.

Defaults to a dry run, same convention as `prune_orphan_logins`/
`release_login`. Pass --apply to actually delete.

    python manage.py purge_demo_catalog            # report only
    python manage.py purge_demo_catalog --apply     # actually delete
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.management.commands.seed_bd_store import CATEGORIES as DEMO_CATEGORIES
from catalog.management.commands.seed_store_catalog import ADOPT_LEGACY, TAXONOMY
from catalog.models import Categories, Products, ProductVariant
from orders.models import OrderItem

DEMO_IMAGE_MARKER = "loremflickr.com"
DEMO_SKU_PREFIX = "FT-"


def _flatten_taxonomy_slugs(nodes):
    slugs = set()
    for slug, _name, _desc, children in nodes:
        slugs.add(slug)
        slugs.update(_flatten_taxonomy_slugs(children))
    return slugs


def _protected_taxonomy_slugs():
    """Every slug that belongs to the real TAXONOMY tree, including the
    legacy demo-category slugs (`mens-fashion`/`womens-fashion`) that
    `seed_store_catalog.ADOPT_LEGACY` reparents *in place* rather than
    replacing -- those rows keep their original slug but now serve as
    permanent taxonomy nodes (parents of `men-tshirts` etc.), so they must
    never be treated as demo data even though their slug isn't literally
    written in TAXONOMY."""
    return _flatten_taxonomy_slugs(TAXONOMY) | set(ADOPT_LEGACY.keys())


def _is_demo_image(image):
    return isinstance(image, list) and any(
        isinstance(url, str) and DEMO_IMAGE_MARKER in url for url in image
    )


class Command(BaseCommand):
    help = "Delete the loremflickr demo catalog seeded by seed_bd_store. Dry run by default."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true",
                            help="Actually delete. Without this it only reports.")

    def handle(self, *args, **options):
        apply = options["apply"]

        demo_products = [p for p in Products.objects.all() if _is_demo_image(p.image)]
        sku_corroborated = sum(1 for p in demo_products if p.sku.startswith(DEMO_SKU_PREFIX))
        self.stdout.write(
            f"Found {len(demo_products)} demo product(s) by image host "
            f"({DEMO_IMAGE_MARKER!r}); {sku_corroborated} of those also carry "
            f"the {DEMO_SKU_PREFIX!r} SKU prefix (corroborating, not used to decide)."
        )

        to_delete, skipped = [], []
        for product in demo_products:
            variant_ids = list(ProductVariant.objects.filter(product=product).values_list("id", flat=True))
            order_count = OrderItem.objects.filter(variant_id__in=variant_ids).count() if variant_ids else 0
            if order_count:
                skipped.append((product, order_count))
            else:
                to_delete.append(product)

        if skipped:
            self.stdout.write(self.style.WARNING(
                f"\nSkipping {len(skipped)} demo product(s) referenced by an order "
                f"(deleting them would corrupt order history):"))
            for product, order_count in skipped:
                self.stdout.write(
                    f"  #{product.id:<5} {product.sku:<12} {product.name!r:<40} "
                    f"-- referenced by {order_count} order item(s)")

        self.stdout.write(f"\n{'Would delete' if not apply else 'Deleting'} {len(to_delete)} demo product(s):")
        for product in to_delete:
            self.stdout.write(f"  #{product.id:<5} {product.sku:<12} {product.name}")

        emptied_categories = []
        if to_delete:
            deleted_category_ids = {p.category_id_id for p in to_delete if p.category_id_id}
            protected = _protected_taxonomy_slugs()
            demo_category_slugs = {c["slug"] for c in DEMO_CATEGORIES} - protected
            candidates = Categories.objects.filter(
                slug__in=demo_category_slugs, id__in=deleted_category_ids,
            )
            for category in candidates:
                # Re-check against the post-delete world, not the pre-delete
                # snapshot: a category can hold both demo and real products,
                # and only a TRULY empty category (no products at all, demo
                # or real) is safe to remove.
                still_has_products = Products.objects.filter(category_id=category).exclude(
                    id__in=[p.id for p in to_delete]
                ).exists()
                has_children = Categories.objects.filter(parent_id=category.id).exists()
                if not still_has_products and not has_children:
                    emptied_categories.append(category)

        if emptied_categories:
            self.stdout.write(
                f"\n{'Would remove' if not apply else 'Removing'} "
                f"{len(emptied_categories)} emptied demo categor{'y' if len(emptied_categories) == 1 else 'ies'}:")
            for category in emptied_categories:
                self.stdout.write(f"  #{category.id:<5} {category.slug:<20} {category.name}")

        if not apply:
            self.stdout.write(self.style.WARNING(
                "\nDry run -- nothing deleted. Re-run with --apply to actually purge."))
            return

        with transaction.atomic():
            Products.objects.filter(id__in=[p.id for p in to_delete]).delete()
            Categories.objects.filter(id__in=[c.id for c in emptied_categories]).delete()

        self.stdout.write(self.style.SUCCESS(
            f"\nDeleted {len(to_delete)} demo product(s) and "
            f"{len(emptied_categories)} emptied demo categor{'y' if len(emptied_categories) == 1 else 'ies'}."
        ))
