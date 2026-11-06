"""NobleSeek taxonomy reconciliation and historical demo cleanup safety."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from nobleseek.category_catalog import NEWS_CATEGORY_CATALOG
from nobleseek.management.commands.cleanup_demo_news import DEMO_ARTICLES, DEMO_BODY_MARKER
from nobleseek.models import Article, FlatPage, NewsCategory


class ReconcileNewsCategoriesTests(TestCase):
    def test_dry_run_then_apply_preserves_ids_slugs_and_custom_rows(self):
        existing = NewsCategory.objects.create(
            name="Tech", slug="tech", display_order=99,
            description="editorial", is_active=False)
        custom = NewsCategory.objects.create(name="Custom", slug="custom", display_order=80)
        article = Article.objects.create(
            headline="real story", body_html="<p>Reported story.</p>",
            category=existing, status=Article.Status.PUBLISHED)

        output = StringIO()
        call_command("reconcile_news_categories", stdout=output)
        assert "Dry run" in output.getvalue()
        assert NewsCategory.objects.count() == 2
        assert NewsCategory.objects.get(pk=existing.pk).name == "Tech"

        call_command("reconcile_news_categories", apply=True, stdout=StringIO())
        existing.refresh_from_db()
        custom.refresh_from_db()
        article.refresh_from_db()
        assert NewsCategory.objects.count() == len(NEWS_CATEGORY_CATALOG) + 1
        assert existing.pk == article.category_id
        assert existing.slug == "tech"
        assert existing.name == "প্রযুক্তি ও স্টার্টআপ"
        assert existing.display_order == 8
        assert existing.description == "editorial"
        assert not existing.is_active
        assert custom.name == "Custom" and custom.display_order == 80
        assert NewsCategory.objects.get(slug="multimedia").name == "মাল্টিমিডিয়া"
        assert NewsCategory.objects.get(slug="ai").name == "কৃত্রিম বুদ্ধিমত্তা"

        second = StringIO()
        call_command("reconcile_news_categories", apply=True, stdout=second)
        assert "0 category changes" in second.getvalue()
        assert NewsCategory.objects.get(slug="tech").pk == existing.pk

    def test_legacy_seed_is_category_only(self):
        call_command("seed_nobleseek", stdout=StringIO())
        assert NewsCategory.objects.count() == len(NEWS_CATEGORY_CATALOG)
        assert Article.objects.count() == 0
        assert FlatPage.objects.count() == 0


class CleanupDemoNewsTests(TestCase):
    def setUp(self):
        slug, headline, excerpt = DEMO_ARTICLES[0]
        self.category = NewsCategory.objects.create(name="Bangladesh", slug=slug)
        self.headline = headline
        self.excerpt = excerpt
        self.body = f"<p><strong>{headline}</strong></p><p>{DEMO_BODY_MARKER}</p>"

    def make_article(self, **overrides):
        values = dict(category=self.category, headline=self.headline,
                      excerpt=self.excerpt, body_html=self.body,
                      status=Article.Status.PUBLISHED)
        values.update(overrides)
        return Article.objects.create(**values)

    def test_dry_run_apply_and_repeat_archive_exact_fixture(self):
        demo = self.make_article()
        output = StringIO()
        call_command("cleanup_demo_news", stdout=output)
        assert f"id={demo.pk}" in output.getvalue()
        demo.refresh_from_db()
        assert demo.status == Article.Status.PUBLISHED

        applied = StringIO()
        call_command("cleanup_demo_news", apply=True, stdout=applied)
        demo.refresh_from_db()
        assert demo.status == Article.Status.ARCHIVED
        assert f"id={demo.pk}" in applied.getvalue()
        assert "Archived: 1" in applied.getvalue()
        public = APIClient().get("/api/store/nobleseek/articles/")
        assert public.status_code == 200
        assert demo.pk not in [article["id"] for article in public.json()["results"]]

        repeated = StringIO()
        call_command("cleanup_demo_news", apply=True, stdout=repeated)
        assert "Archived: 0" in repeated.getvalue()
        assert Article.objects.filter(pk=demo.pk).exists()

    def test_real_or_edited_articles_are_not_archived(self):
        wrong_category = NewsCategory.objects.create(name="World", slug="world")
        near_matches = [
            self.make_article(excerpt="real reporting"),
            self.make_article(category=wrong_category),
            self.make_article(body_html="<p>Original reporting.</p>"),
            self.make_article(body_html=f"<p>{DEMO_BODY_MARKER}</p>"),
            self.make_article(status=Article.Status.DRAFT),
            self.make_article(content_type=Article.ContentType.BLOG),
            self.make_article(headline="Real story with a different headline"),
        ]
        call_command("cleanup_demo_news", apply=True, stdout=StringIO())
        assert set(Article.objects.filter(status=Article.Status.ARCHIVED).values_list("pk", flat=True)) == set()
        assert Article.objects.filter(pk__in=[article.pk for article in near_matches]).count() == len(near_matches)


class PublicCategoryOrderTests(TestCase):
    def test_aggregate_counts_preserve_editorial_menu_order(self):
        from django.core.cache import cache
        cache.clear()
        NewsCategory.objects.create(slug="later", name="A later", display_order=8)
        NewsCategory.objects.create(slug="first", name="Z first", display_order=0)
        response = self.client.get("/api/store/nobleseek/categories/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["slug"] for row in response.json()["data"]], ["first", "later"])
