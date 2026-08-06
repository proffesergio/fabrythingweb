"""Clear stock-photo placeholder imagery off the live CATEGORY rows.

`purge_demo_catalog` already removed the demo *products* that carried
loremflickr images. What it never touched is the handful of **category** rows
whose `image` still points at a random-stock-photo service — production is
currently serving three of them (Eyewear, Fashion > Men, Fashion > Women)
while the other ~47 categories carry no image at all.

Why clear rather than leave them:

- The URL returns a *different random photo on every request*, so the category
  tile advertises whatever loremflickr feels like — for a shop taking real
  money that reads as unfinished at best and as someone else's product at
  worst.
- It is a third-party host on the critical render path. When loremflickr is
  slow or gone the tile is a broken image, and nothing about our uptime
  changes that.
- Empty is a *supported* state, not a degradation: 47 of 50 categories already
  have no image and the storefront renders them fine, so clearing these three
  makes production consistent instead of introducing a new case.

Real photography can be attached later from the admin panel per category;
this command deliberately does not invent a replacement.

Dry run by default. Same two-stage, env-gated deploy pattern as
`purge_demo_catalog` — there is no shell on Render's free plan:

    python manage.py clear_placeholder_media            # report only
    python manage.py clear_placeholder_media --apply    # actually clear
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import Categories

# Random-stock-photo services. A category image on any of these is decorative
# filler by definition — none of them can return *our* product.
PLACEHOLDER_IMAGE_HOSTS = (
    "loremflickr.com",
    "via.placeholder.com",
    "placehold.it",
    "placehold.co",
    "picsum.photos",
    "dummyimage.com",
)


def placeholder_urls(image):
    """The placeholder URLs inside a Categories.image value.

    `image` is a JSON list in practice but has been a bare string on older
    rows, so handle both rather than assuming — a TypeError here would abort
    a deploy step.
    """
    if isinstance(image, str):
        urls = [image]
    elif isinstance(image, list):
        urls = [u for u in image if isinstance(u, str)]
    else:
        return []
    return [u for u in urls if any(host in u for host in PLACEHOLDER_IMAGE_HOSTS)]


class Command(BaseCommand):
    help = ("Clear stock-photo placeholder images off category rows. "
            "Dry run by default; pass --apply to write.")

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true",
                            help="Actually clear the images. Without this it only reports.")

    def handle(self, *args, **options):
        apply = options["apply"]

        affected = []
        for category in Categories.objects.all():
            hits = placeholder_urls(category.image)
            if hits:
                affected.append((category, hits))

        if not affected:
            self.stdout.write("No category is using a placeholder image host — nothing to do.")
            return

        self.stdout.write(f"{len(affected)} category/categories using placeholder imagery:")
        for category, hits in affected:
            self.stdout.write(f"  - {category.name} (slug={category.slug}): {', '.join(hits)}")

        if not apply:
            self.stdout.write(self.style.WARNING(
                "\nDry run — nothing written. Re-run with --apply to clear these."))
            return

        with transaction.atomic():
            for category, _hits in affected:
                # Keep any non-placeholder URL that happens to sit alongside a
                # placeholder one: a category with one real photo and one filler
                # should end up with the real photo, not with nothing.
                kept = [u for u in (category.image or []) if not placeholder_urls([u])] \
                    if isinstance(category.image, list) else []
                category.image = kept
                category.save(update_fields=["image"])

        self.stdout.write(self.style.SUCCESS(
            f"\nCleared placeholder imagery from {len(affected)} category/categories."))
