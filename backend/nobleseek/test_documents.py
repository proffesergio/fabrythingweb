"""Public crawlability: real HTML, canonical hosts and truthful missing URLs."""
import json
from datetime import timedelta
from xml.etree import ElementTree as ET

from django.test import TestCase
from django.utils import timezone

from .models import Article, NewsCategory, PublishingSettings

BASE = "/api/store/nobleseek/"


class NewsDocumentTests(TestCase):
    def setUp(self):
        PublishingSettings.objects.update_or_create(pk=1, defaults={"news_site_url": "https://nobleseek.fabrything.com"})
        self.article = Article.objects.create(
            headline="News headline", headline_bn="বাংলা সংবাদ", slug="বাংলা-সংবাদ",
            excerpt="A useful description", body_html='<p>Real report.</p><script>alert(1)</script>',
            status="PUBLISHED", hero_image="/api/media/example/", source_name="Primary source",
            source_url="https://example.com/source",
        )

    def test_real_article_and_metadata_are_available_without_javascript(self):
        response = self.client.get(BASE + "document/বাংলা-সংবাদ/", HTTP_HOST="api.example.com")
        self.assertContains(response, "Real report.")
        self.assertContains(response, '<h1>বাংলা সংবাদ</h1>', html=True)
        self.assertContains(response, "Primary source")
        self.assertContains(response, 'name="google-adsense-account" content="ca-pub-1712742966437949"')
        self.assertContains(response, 'href="' + self.article.get_canonical_url() + '"')
        self.assertNotContains(response, "alert(1)")
        self.assertNotContains(response, "api.example.com")
        html = response.content.decode()
        schema = json.loads(html.split('type="application/ld+json">')[1].split('</script>')[0])
        self.assertEqual(schema["@type"], "NewsArticle")
        self.assertEqual(schema["headline"], "বাংলা সংবাদ")
        self.assertEqual(schema["image"], ["https://nobleseek.fabrything.com/api/media/example/"])
        self.assertEqual(schema["mainEntityOfPage"]["@id"], self.article.get_canonical_url())

    def test_missing_draft_future_and_blog_articles_return_404(self):
        for slug, kwargs in [("draft", {"status": "DRAFT"}),
                             ("future", {"published_at": timezone.now() + timedelta(days=1)}),
                             ("blog", {"content_type": "BLOG"})]:
            Article.objects.create(headline=slug, slug=slug, body_html="<p>Hidden</p>", status=kwargs.pop("status", "PUBLISHED"), **kwargs)
        for slug in ("missing", "draft", "future", "blog"):
            self.assertEqual(self.client.get(BASE + "document/" + slug + "/").status_code, 404)

    def test_archives_link_to_later_pages_and_validate_page_numbers(self):
        for index in range(13):
            Article.objects.create(headline=f"Report {index}", body_html="<p>Report</p>", status="PUBLISHED")
        response = self.client.get(BASE + "document/")
        self.assertContains(response, "https://nobleseek.fabrything.com/nobleseek?page=2")
        response = self.client.get(BASE + "document/?page=2")
        self.assertContains(response, 'rel="canonical" href="https://nobleseek.fabrything.com/nobleseek?page=2"')
        for page in ("0", "-1", "invalid", "9999"):
            self.assertEqual(self.client.get(BASE + "document/?page=" + page).status_code, 404)

    def test_search_empty_archives_and_section_canonicals(self):
        category = NewsCategory.objects.create(name="Technology", slug="technology")
        self.article.category = category
        self.article.save()
        response = self.client.get(BASE + "document/?category=technology")
        self.assertContains(response, 'rel="canonical" href="https://nobleseek.fabrything.com/nobleseek?category=technology"')
        self.assertContains(self.client.get(BASE + "document/?search=notfound"), 'content="noindex,follow"')
        self.assertEqual(self.client.get(BASE + "document/?category=missing").status_code, 404)

    def test_trust_pages_have_canonical_and_useful_fallback(self):
        for page in ("about", "contact", "privacy", "disclaimer", "ethics"):
            response = self.client.get(BASE + "document/" + page + "/")
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "support@fabrything.com")

    def test_news_sitemap_marks_only_recent_news_with_news_metadata(self):
        Article.objects.create(headline="Old report", slug="old", body_html="<p>Old</p>", status="PUBLISHED", published_at=timezone.now() - timedelta(days=3))
        Article.objects.create(headline="Future report", slug="future", body_html="<p>Future</p>", status="PUBLISHED", published_at=timezone.now() + timedelta(days=1))
        root = ET.fromstring(self.client.get(BASE + "sitemap.xml").content)
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9", "n": "http://www.google.com/schemas/sitemap-news/0.9"}
        news = root.findall("s:url/n:news", ns)
        self.assertEqual(len(news), 1)
        self.assertEqual(news[0].find("n:title", ns).text, "বাংলা সংবাদ")
        self.assertEqual(news[0].find("n:publication/n:language", ns).text, "bn")
        locations = [n.text for n in root.findall("s:url/s:loc", ns)]
        self.assertIn("https://nobleseek.fabrything.com/nobleseek/old", locations)
        self.assertNotIn("https://nobleseek.fabrything.com/nobleseek/future", locations)
