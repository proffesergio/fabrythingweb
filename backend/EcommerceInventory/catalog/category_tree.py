"""Single definition of "this category's whole subtree", shared by the
storefront category filter (``storefront.views.PublicProductListView``) and
the category product-count serializer (``storefront.serializers.
StorefrontCategorySerializer.get_product_count``).

BUG 2: both call sites used to collect only *direct children* of the
requested category (``Categories.objects.filter(parent_id=category.id)``).
The storefront taxonomy is three levels deep — ``fashion > Men > T-shirts``
— and products live in the leaves, so filtering by a top-level category like
``fashion`` missed every grandchild. Verified live: ``?category=fashion``
returned 16 products when Fashion actually holds 64. One reusable
breadth-first walk fixes both call sites at once and can't drift apart again.
"""
from catalog.models import Categories


def descendant_category_ids(category):
    """Return ``[category.id, ...every id below it in the tree]``.

    Breadth-first over ``parent_id``, tracking visited ids so a cyclic
    ``parent_id`` (nothing stops one admin edit from pointing a category at
    its own descendant — the FK is self-referencing) terminates instead of
    hanging the request.
    """
    seen = {category.id}
    frontier = [category.id]
    while frontier:
        children = list(
            Categories.objects.filter(parent_id__in=frontier)
            .exclude(id__in=seen)
            .values_list('id', flat=True)
        )
        if not children:
            break
        seen.update(children)
        frontier = children
    return list(seen)
