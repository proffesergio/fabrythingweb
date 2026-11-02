"""Copying a menu from one restaurant to another.

Onboarding a new restaurant usually means retyping a menu that already exists
somewhere on the platform. This copies it instead.

Matching is by name: a category whose name already exists in the target is
merged into, and an item whose name already exists in that target category is
skipped. That makes a re-run a no-op rather than a duplicate, so an admin can
copy again after adding a few dishes to the source.
"""
from django.db import transaction

from food.models import FoodCategory, FoodItem, FoodItemOptionGroup, FoodItemOption
from food.views_vendor import _unique_item_slug

ITEM_FIELDS = [
    "name", "name_bn", "description", "description_bn", "image", "price", "discount_price",
    "prep_minutes", "is_available", "is_veg", "is_featured", "tags", "available_from",
    "available_to", "available_days", "spice_level", "display_order",
]


def _copy_options(source_item, new_item, counters, dry_run):
    for group in source_item.option_groups.all():
        options = list(group.options.all())
        counters["options_copied"] += len(options)
        if dry_run:
            continue
        new_group = FoodItemOptionGroup.objects.create(
            item=new_item, name=group.name, name_bn=group.name_bn,
            min_select=group.min_select, max_select=group.max_select,
            is_required=group.is_required,
        )
        for option in options:
            FoodItemOption.objects.create(
                group=new_group, name=option.name, name_bn=option.name_bn,
                price_delta=option.price_delta, is_default=option.is_default,
                display_order=option.display_order,
            )


def copy_menu(source, target, item_ids=None, target_category=None, dry_run=False):
    """Copy source's menu into target. Returns counts; writes nothing if dry_run.

    item_ids        — copy only these items (a selective copy); None copies everything.
    target_category — force every copied item into this category; None mirrors the
                      source's own category structure.
    """
    counters = {"categories_created": 0, "categories_merged": 0,
                "items_copied": 0, "items_skipped": 0, "options_copied": 0}

    items = FoodItem.objects.filter(restaurant=source).select_related("category_id")
    if item_ids is not None:
        items = items.filter(id__in=item_ids)

    with transaction.atomic():
        # Source category name → resolved target category. Built lazily so a dry
        # run can still count creations without performing them.
        resolved = {}

        for item in items:
            if target_category is not None:
                destination = target_category
            else:
                source_name = item.category_id.name
                if source_name not in resolved:
                    existing = FoodCategory.objects.filter(restaurant=target, name=source_name).first()
                    if existing:
                        counters["categories_merged"] += 1
                        resolved[source_name] = existing
                    else:
                        counters["categories_created"] += 1
                        resolved[source_name] = None if dry_run else FoodCategory.objects.create(
                            restaurant=target, name=source_name,
                            name_bn=item.category_id.name_bn,
                            display_order=item.category_id.display_order,
                        )
                destination = resolved[source_name]

            # Same dish already on the target's menu → leave it alone.
            duplicate = FoodItem.objects.filter(restaurant=target, name=item.name)
            if destination is not None:
                duplicate = duplicate.filter(category_id=destination)
            if duplicate.exists():
                counters["items_skipped"] += 1
                continue

            counters["items_copied"] += 1
            if dry_run or destination is None:
                continue

            values = {f: getattr(item, f) for f in ITEM_FIELDS}
            new_item = FoodItem.objects.create(
                restaurant=target, category_id=destination,
                slug=_unique_item_slug(target, item.name), **values,
            )
            _copy_options(item, new_item, counters, dry_run)

        if dry_run:
            transaction.set_rollback(True)

    return counters
