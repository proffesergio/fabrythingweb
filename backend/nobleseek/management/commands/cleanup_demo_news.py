"""Archive only the exact historical NobleSeek article fixtures."""

from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import transaction

from nobleseek.models import Article


# These are the five entries the old seed_nobleseek command published.
# A title alone, low ID, or category alone is never enough to select a row.
DEMO_ARTICLES = (
    ("bangladesh", "ঢাকায় মেট্রোরেলের নতুন রুট: যা জানা জরুরি | Dhaka Metro New Route",
     "মেট্রোরেলের নতুন অংশের সময়সূচি, ভাড়া ও যাত্রী নির্দেশনা নিয়ে বিস্তারিত।"),
    ("sports", "বাংলাদেশ বনাম ভারত: টানটান উত্তেজনার ম্যাচ | BAN vs IND Thriller",
     "শেষ ওভারের নাটকীয়তা, স্কোরকার্ড ও প্রতিক্রিয়া।"),
    ("tech", "iPhone 17 price in Bangladesh: full breakdown",
     "অফিসিয়াল ও গ্রে-মার্কেট দাম, স্পেসিফিকেশন ও কেনার পরামর্শ।"),
    ("world", "Bitcoin price surges: what it means for BD investors",
     "বিশ্ববাজারের ঊর্ধ্বগতি ও বাংলাদেশি বিনিয়োগকারীদের করণীয়।"),
    ("entertainment", "নতুন ওয়েব সিরিজে ঝড় তুললেন জনপ্রিয় অভিনেতা | Viral Web Series",
     "গল্প, অভিনয় ও দর্শক প্রতিক্রিয়া নিয়ে রিভিউ।"),
)
DEMO_BY_HEADLINE = {headline: (slug, excerpt) for slug, headline, excerpt in DEMO_ARTICLES}
DEMO_BODY_MARKER = "NobleSeek ডেমো প্রতিবেদন। এখানে ৬০০-৮০০ শব্দের মূল প্রতিবেদন লিখুন।"


def is_exact_demo(article):
    expected = DEMO_BY_HEADLINE.get(article.headline)
    return bool(
        expected
        and article.content_type == Article.ContentType.NEWS
        and article.status == Article.Status.PUBLISHED
        and article.category is not None
        and article.category.slug == expected[0]
        and article.excerpt == expected[1]
        and article.body_html.startswith(f"<p><strong>{article.headline}</strong></p>")
        and DEMO_BODY_MARKER in article.body_html
    )


class Command(BaseCommand):
    help = "Dry-run exact historical demo matches; --apply archives them without deletion."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Archive exact matches")

    def handle(self, *args, **options):
        apply = options["apply"]
        with transaction.atomic():
            queryset = Article.objects.select_related("category").filter(
                headline__in=DEMO_BY_HEADLINE,
                status=Article.Status.PUBLISHED,
                content_type=Article.ContentType.NEWS,
            )
            if apply:
                queryset = queryset.select_for_update(of=("self",))
            matches = [article for article in queryset if is_exact_demo(article)]
            for article in matches:
                self.stdout.write(f"id={article.pk} title={article.headline} status={article.status}")
                if apply:
                    article.status = Article.Status.ARCHIVED
                    article.save(update_fields=["status", "updated_at"])
            if apply and matches:
                transaction.on_commit(lambda: cache.delete_many(
                    ["nobleseek:categories", "nobleseek:latest4"]))
        self.stdout.write(f"{'Archived' if apply else 'Dry run'}: {len(matches)} exact demo article(s)")
