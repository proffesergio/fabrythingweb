"""Canonical NobleSeek sections shared by the CLI and admin restore action.

Slugs are stable API keys (and may be referenced by n8n); reconciliation never
reassigns a category ID or changes an existing slug.
"""

from django.core.cache import cache
from django.db import transaction

from .models import NewsCategory


# Union of the observed TBS News Bangla and Daily Star Bangla sections, with
# NobleSeek's existing sections retained. The order is the public menu order.
NEWS_CATEGORY_CATALOG = (
    ("bangladesh", "বাংলাদেশ"),
    ("politics", "রাজনীতি"),
    ("world", "আন্তর্জাতিক"),
    ("economy", "অর্থনীতি"),
    ("business", "বাণিজ্য"),
    ("sports", "খেলা"),
    ("entertainment", "বিনোদন"),
    ("lifestyle", "জীবনযাপন"),
    ("tech", "প্রযুক্তি ও স্টার্টআপ"),
    ("opinion", "মতামত"),
    ("analysis", "বিশ্লেষণ"),
    ("explainer", "এক্সপ্লেইনার"),
    ("feature", "ফিচার"),
    ("culture", "সংস্কৃতি"),
    ("easel", "ইজেল"),
    ("offbeat", "অফবিট"),
    ("country", "সারাদেশ"),
    ("corporate", "কর্পোরেট"),
    ("jobs", "চাকরি"),
    ("expatriate", "প্রবাস"),
    ("education", "শিক্ষা"),
    ("health", "স্বাস্থ্য"),
    ("environment", "পরিবেশ"),
    ("crime", "অপরাধ"),
    ("court", "আদালত"),
    ("video", "ভিডিও"),
    ("multimedia", "মাল্টিমিডিয়া"),
    ("ai", "কৃত্রিম বুদ্ধিমত্তা"),
)


def reconcile_categories(*, apply=False):
    """Return a plan, or apply it without touching noncatalog categories.

    Existing category IDs, slugs, parent links, descriptions and active flags
    are preserved. Only canonical names and menu positions are updated.
    """
    with transaction.atomic():
        existing = {category.slug: category for category in NewsCategory.objects.all()}
        changes = []
        for order, (slug, name) in enumerate(NEWS_CATEGORY_CATALOG):
            category = existing.get(slug)
            if category is None:
                changes.append({"action": "create", "slug": slug, "name": name, "display_order": order})
                if apply:
                    NewsCategory.objects.create(slug=slug, name=name, display_order=order)
                continue
            fields = []
            if category.name != name:
                fields.append("name")
            if category.display_order != order:
                fields.append("display_order")
            if fields:
                changes.append({"action": "update", "id": category.pk, "slug": slug,
                                "name": name, "display_order": order})
                if apply:
                    category.name = name
                    category.display_order = order
                    category.save(update_fields=fields)
        if apply and changes:
            transaction.on_commit(lambda: cache.delete("nobleseek:categories"))
    return changes
