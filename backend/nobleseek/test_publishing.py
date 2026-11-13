"""Publishing contract, staff authorization, ingestion policy and sanitization."""
from datetime import timedelta
from unittest.mock import patch
from xml.etree import ElementTree

from django.core.cache import cache
from django.db import DatabaseError
from django.test import TestCase, SimpleTestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import Users
from .models import Article, NewsCategory, PublishingSettings
from .sanitization import sanitize_article_html
from .services_publishing import daily_window
from .views_operations import database_size


BASE = "/api/store/nobleseek/"


class PublishingTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.staff = Users.objects.create_user(username="publisher", email="publisher@example.com",
                                               password="test", address="Dhaka", role="Super Admin")
        self.staff_client = APIClient()
        self.staff_client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(self.staff)}")

    def article(self, **kwargs):
        return Article.objects.create(**{
            "headline": "Example story", "body_html": "<p>Example body</p>",
            "status": Article.Status.PUBLISHED, **kwargs})

    def create(self, **kwargs):
        return self.staff_client.post(BASE + "admin/articles/", {
            "headline": "Created story", "body_html": "<p>Example body</p>", **kwargs}, format="json")

    def settings(self, **kwargs):
        response = self.staff_client.patch(BASE + "admin/publishing-settings/", kwargs, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["data"]

    def test_news_and_blog_isolation_and_scheduling(self):
        category = NewsCategory.objects.create(name="Products", slug="products")
        news = self.article(category=category)
        blog = self.article(headline="Blog article", content_type="BLOG", category=category)
        self.article(headline="Blog draft", content_type="BLOG", status="DRAFT")
        self.article(headline="Blog scheduled", content_type="BLOG",
                     published_at=timezone.now() + timedelta(days=1))
        self.assertEqual([row["id"] for row in self.client.get(BASE + "blog/").data["results"]], [blog.pk])
        self.assertEqual([row["id"] for row in self.client.get(BASE + "articles/").data["results"]], [news.pk])
        self.assertEqual(self.client.get(BASE + f"articles/{blog.slug}/").status_code, 404)
        self.assertEqual(self.client.get(BASE + f"blog/{news.slug}/").status_code, 404)
        self.assertEqual(self.client.get(BASE + f"articles/{blog.slug}/related/").status_code, 404)
        self.assertEqual(self.client.get(BASE + "latest/").data["data"][0]["id"], news.pk)
        self.assertEqual(self.client.get(BASE + "rss-data/").data["data"]["items"][0]["id"], news.pk)
        self.assertEqual(self.client.get(BASE + "categories/").data["data"][0]["article_count"], 1)
        self.assertNotIn(blog.slug, str(self.client.get(BASE + "sitemap-data/").data))

    def test_jsonld_and_canonical_never_use_api_host(self):
        news = self.article(slug="news-story")
        blog = self.article(slug="blog-story", content_type="BLOG", hero_image="/api/media/abc/")
        response = self.client.get(BASE + f"blog/{blog.slug}/", HTTP_HOST="backend.example.com")
        data = response.data["data"]
        self.assertEqual(data["canonical_url"], "https://www.fabrything.com/blog/blog-story")
        self.assertEqual(data["json_ld"]["@type"], "BlogPosting")
        self.assertEqual(data["json_ld"]["mainEntityOfPage"]["@id"], data["canonical_url"])
        self.assertTrue(data["json_ld"]["image"][0].startswith("http"))
        self.settings(news_site_url="https://news.fabrything.com/")
        response = self.client.get(BASE + f"articles/{news.slug}/", HTTP_HOST="backend.example.com")
        self.assertEqual(response.data["data"]["canonical_url"], "https://news.fabrything.com/nobleseek/news-story")
        self.assertEqual(response.data["data"]["json_ld"]["@type"], "NewsArticle")
        self.assertEqual(self.client.get(BASE + "rss-data/").data["data"]["site"], "https://news.fabrything.com")

    def test_sitemap_blog_and_news_configured_origin_and_visibility(self):
        self.settings(news_site_url="https://news.fabrything.com")
        news = self.article(slug="news-story")
        blog = self.article(slug="বাংলা-ব্লগ", content_type="BLOG")
        hidden = self.article(slug="hidden-blog", content_type="BLOG", status="DRAFT")
        future = self.article(slug="future-blog", content_type="BLOG",
                              published_at=timezone.now() + timedelta(days=1))
        response = self.client.get("/api/store/sitemap.xml")
        root = ElementTree.fromstring(response.content)
        urls = {node.text for node in root.findall("{*}url/{*}loc")}
        self.assertNotIn(news.get_canonical_url(), urls)
        news_map = self.client.get('/api/store/nobleseek/sitemap.xml')
        news_urls = {node.text for node in ElementTree.fromstring(news_map.content).findall('{*}url/{*}loc')}
        self.assertIn(news.get_canonical_url(), news_urls)
        self.assertIn(blog.get_canonical_url(), urls)
        self.assertIn("https://www.fabrything.com/blog", urls)
        self.assertNotIn(hidden.get_canonical_url(), urls)
        self.assertNotIn(future.get_canonical_url(), urls)
        self.assertNotIn("https://news.fabrything.com/nobleseek/" + blog.slug, urls)

    def test_default_settings_preserve_existing_automation(self):
        data = self.staff_client.get(BASE + "admin/publishing-settings/").data["data"]
        self.assertFalse(data["ingestion_paused"])
        self.assertEqual(data["daily_article_limit"], 0)
        self.assertFalse(data["require_review_for_automation"])
        response = self.create(status="PUBLISHED")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["content_type"], "NEWS")
        self.assertEqual(response.data["status"], "PUBLISHED")
        self.assertNotIn("automation", response.data)

    def test_settings_reject_negative_limits_and_non_origin_urls(self):
        for fields in ({"daily_article_limit": -1}, {"estimated_image_bytes_per_article": -1},
                       {"news_site_url": "https://example.com/path"},
                       {"news_site_url": "javascript:alert(1)"},
                       {"news_site_url": "https://user:pass@example.com"}):
            response = self.staff_client.patch(BASE + "admin/publishing-settings/", fields, format="json")
            self.assertEqual(response.status_code, 400, response.data)

    def test_pause_blocks_creates_but_not_editor_updates(self):
        article = self.article()
        self.settings(ingestion_paused=True)
        response = self.create()
        self.assertEqual(response.status_code, 400)
        self.assertIn("ingestion_paused", response.data)
        response = self.staff_client.patch(BASE + f"admin/articles/{article.pk}/",
                                          {"excerpt": "Edited"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Article.objects.count(), 1)

    def test_daily_cap_counts_all_content_types_and_resets_at_local_midnight(self):
        old = self.article(content_type="BLOG")
        start, _ = daily_window()
        Article.objects.filter(pk=old.pk).update(created_at=start - timedelta(seconds=1))
        self.settings(daily_article_limit=1)
        self.assertEqual(self.create(content_type="BLOG").status_code, 201)
        response = self.create()
        self.assertEqual(response.status_code, 400)
        self.assertIn("daily_article_limit", response.data)
        self.settings(daily_article_limit=0)
        self.assertEqual(self.create().status_code, 201)

    def test_automation_review_opt_in_and_staff_publish_preserved(self):
        self.settings(require_review_for_automation=True)
        response = self.create(status="PUBLISHED", automation=True)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], "REVIEW")
        self.assertEqual(self.create(status="PUBLISHED").data["status"], "PUBLISHED")
        self.assertEqual(self.create(status="DRAFT", automation=True).data["status"], "DRAFT")

    def test_staff_jwt_required_before_policy_is_exposed(self):
        self.settings(ingestion_paused=True, daily_article_limit=1)
        customer = Users.objects.create_user(username="customer", email="customer@example.com",
                                            password="test", address="Dhaka", role="Customer")
        for client, expected in ((self.client, 401), (APIClient(), 403)):
            if expected == 403:
                client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(customer)}")
            for method, path, data in (("get", "admin/operations/", {}),
                                       ("get", "admin/publishing-settings/", {}),
                                       ("patch", "admin/publishing-settings/", {"ingestion_paused": False}),
                                       ("post", "admin/articles/", {"headline": "x", "body_html": "y"})):
                response = getattr(client, method)(BASE + path, data, format="json")
                self.assertEqual(response.status_code, expected, response.data)
                self.assertNotIn("ingestion_paused", str(response.data))

    def test_admin_body_sanitized_on_create_and_update(self):
        payload = '<p onclick="evil()">Safe <strong>bold</strong></p><script>evil()</script><img src="/safe.jpg" onerror="evil()"><a href="javascript:evil()">bad</a>'
        response = self.create(body_html=payload, content_type="BLOG")
        self.assertEqual(response.status_code, 201, response.data)
        body = response.data["body_html"]
        self.assertNotIn("evil", body)
        self.assertIn("<strong>bold</strong>", body)
        self.assertIn('src="/safe.jpg"', body)
        response = self.staff_client.patch(BASE + f'admin/articles/{response.data["id"]}/',
                                          {"body_html": payload}, format="json")
        self.assertEqual(response.data["body_html"], body)

    def test_admin_list_filters_content_type(self):
        self.article()
        blog = self.article(content_type="BLOG")
        response = self.staff_client.get(BASE + "admin/articles/", {"content_type": "BLOG"})
        self.assertEqual([row["id"] for row in response.data["results"]], [blog.pk])

    def test_view_counter_uses_atomic_cache_claim(self):
        article = self.article()
        path = BASE + f"articles/{article.slug}/"
        self.client.get(path, REMOTE_ADDR="10.0.0.1")
        self.client.get(path, REMOTE_ADDR="10.0.0.1")
        self.client.get(path, REMOTE_ADDR="10.0.0.2")
        article.refresh_from_db()
        self.assertEqual(article.view_count, 2)
        # Simulate another process incrementing after the detail SELECT.
        real_add = cache.add
        def claim_with_concurrent_increment(*args, **kwargs):
            Article.objects.filter(pk=article.pk).update(view_count=10)
            return real_add(*args, **kwargs)
        with patch("nobleseek.views.cache.add", side_effect=claim_with_concurrent_increment):
            self.client.get(path, REMOTE_ADDR="10.0.0.3")
        article.refresh_from_db()
        self.assertEqual(article.view_count, 11)

    def test_operations_actual_counts_bounded_seo_and_estimates(self):
        old = self.article(headline="Old complete", seo_title="Title", seo_description="Description",
                           hero_image="https://example.com/a.jpg", hero_image_alt="Alt")
        Article.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=3),
                                                published_at=timezone.now() - timedelta(days=3))
        for i in range(12):
            self.article(headline=f"Blog {i}", content_type="BLOG", seo_title="  ")
        self.article(headline="Scheduled", published_at=timezone.now() + timedelta(days=1))
        self.article(headline="Draft", status="DRAFT")
        self.settings(estimated_text_bytes_per_article=100, estimated_image_bytes_per_article=200)
        response = self.staff_client.get(BASE + "admin/operations/")
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertEqual(data["counts"]["total"], 15)
        self.assertEqual(data["counts"]["published"], 13)
        self.assertEqual(data["counts"]["scheduled"], 1)
        self.assertEqual(data["production_last_24h"]["created"], 14)
        self.assertEqual(data["production_last_24h"]["published"], 12)
        self.assertEqual(data["seo"]["missing"]["seo_title"], 12)
        self.assertEqual(data["seo"]["missing"]["hero_image_alt"], 0)
        self.assertEqual(len(data["seo"]["samples"]), 10)
        self.assertEqual(data["storage_estimate"]["total_bytes"], 1700)
        self.assertFalse(data["database"]["available"])
        self.assertIsNone(data["database"]["size_bytes"])
        self.assertFalse(data["provider_metrics"]["available"])
        self.assertIsNone(data["provider_metrics"]["storage_limit_bytes"])

    def test_trend_creation_obeys_pause_without_consuming_trend(self):
        from .models import TrendKeyword
        trend = TrendKeyword.objects.create(keyword="Test trend")
        self.settings(ingestion_paused=True)
        with patch("nobleseek.views_admin.ai_draft_for_keyword", return_value={"body_html": "<p>draft</p>"}):
            response = self.staff_client.post(BASE + f"admin/trends/{trend.pk}/create-draft/")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Article.objects.exists())
        trend.refresh_from_db()
        self.assertEqual(trend.status, "NEW")


class SanitizationTests(SimpleTestCase):
    def test_unsafe_namespaces_encoded_protocols_and_malformed_urls_removed(self):
        for payload in ('<svg><script>alert(1)</script></svg>',
                        '<a href="java&#x09;script:alert(1)" onclick="alert(1)">link</a>',
                        '<img src="data:image/svg+xml,test" onerror="alert(1)">',
                        '<iframe src="https://example.com">evil</iframe>',
                        '<a href="https://[invalid">link</a>'):
            result = sanitize_article_html(payload)
            for forbidden in ("script", "alert", "onclick", "onerror", "data:", "iframe", "invalid"):
                self.assertNotIn(forbidden, result)


class DatabaseMeasurementTests(SimpleTestCase):
    def test_postgresql_uses_database_size_and_hides_errors(self):
        with patch("nobleseek.views_operations.connection") as connection, patch("nobleseek.views_operations.transaction.atomic"):
            connection.vendor = "postgresql"
            cursor = connection.cursor.return_value.__enter__.return_value
            cursor.fetchone.return_value = (12345,)
            self.assertEqual(database_size()["size_bytes"], 12345)
            cursor.execute.assert_called_once_with("SELECT pg_database_size(current_database())")
            cursor.execute.side_effect = DatabaseError("secret internal error")
            result = database_size()
            self.assertFalse(result["available"])
            self.assertNotIn("secret", str(result))
