import json
from datetime import timedelta
from io import StringIO
from unittest.mock import patch
from xml.etree import ElementTree

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone

from core.models import ImageBlob
from catalog.models import Products
from .models import Article, PublishingSettings


ORIGIN = "https://nobleseek.fabrything.com"
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class NewsXmlSitemapTests(TestCase):
    def test_canonical_news_and_trust_pages_exclude_blog_and_non_live_news(self):
        policy = PublishingSettings.current()
        policy.news_site_url = ORIGIN
        policy.save()
        news = Article.objects.create(headline="বাংলা সংবাদ", body_html="<p>News</p>", status="PUBLISHED")
        for name, options in (
                ("Blog", {"content_type": "BLOG", "status": "PUBLISHED"}),
                ("Draft", {"status": "DRAFT"}),
                ("Review", {"status": "REVIEW"}),
                ("Archived", {"status": "ARCHIVED"}),
                ("Future", {"status": "PUBLISHED", "published_at": timezone.now() + timedelta(days=1)})):
            Article.objects.create(headline=name, body_html="<p>Other</p>", **options)
        response = self.client.get("/api/store/nobleseek/sitemap.xml", HTTP_HOST="backend.example.com")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml")
        self.assertIn("s-maxage=300", response["Cache-Control"])
        root = ElementTree.fromstring(response.content)
        self.assertEqual(root.tag, "{" + NS["s"] + "}urlset")
        locations = {node.text for node in root.findall("s:url/s:loc", NS)}
        expected = {ORIGIN + "/nobleseek" + suffix for suffix in
                    ("", "/about", "/contact", "/privacy", "/disclaimer", "/ethics")}
        self.assertEqual(locations, expected | {news.get_canonical_url()})
        self.assertEqual(root.find("s:url/s:lastmod", NS).text, news.updated_at.isoformat())
        news.refresh_from_db()
        self.assertEqual(news.view_count, 0)

    def test_default_origin_and_json_contract_remain_compatible_without_writes(self):
        PublishingSettings.objects.all().delete()
        response = self.client.get("/api/store/nobleseek/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"https://www.fabrything.com/nobleseek", response.content)
        response = self.client.get("/api/store/nobleseek/sitemap-data/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("urls", response.json()["data"])
        self.assertFalse(PublishingSettings.objects.exists())


class NewsSiteActivationTests(TestCase):
    def test_activation_idempotent_and_preserves_all_other_configuration(self):
        policy = PublishingSettings.current()
        policy.ingestion_paused = True
        policy.daily_article_limit = 42
        policy.require_review_for_automation = True
        policy.estimated_text_bytes_per_article = 123
        policy.estimated_image_bytes_per_article = 456
        policy.save()
        original = PublishingSettings.objects.values().get(pk=1)
        output = StringIO()
        call_command("set_news_site", origin=ORIGIN, stdout=output)
        self.assertEqual(json.loads(output.getvalue()), {"news_site_url": ORIGIN, "changed": True})
        first = PublishingSettings.objects.values().get(pk=1)
        for key, value in original.items():
            if key not in {"news_site_url", "updated_at"}:
                self.assertEqual(first[key], value)
        output = StringIO()
        call_command("set_news_site", origin=ORIGIN, stdout=output)
        self.assertFalse(json.loads(output.getvalue())["changed"])
        self.assertEqual(PublishingSettings.objects.values().get(pk=1), first)

    def test_invalid_origin_rejected_before_any_database_access(self):
        for origin in ("https://www.fabrything.com", "http://nobleseek.fabrything.com",
                       ORIGIN + "/", ORIGIN + "/nobleseek", ORIGIN + ".evil.example",
                       "https://user:pass@nobleseek.fabrything.com", ""):
            with self.assertNumQueries(0), self.assertRaises(CommandError):
                call_command("set_news_site", origin=origin)

    def test_missing_singleton_created_with_compatible_defaults(self):
        PublishingSettings.objects.all().delete()
        call_command("set_news_site", origin=ORIGIN, stdout=StringIO())
        policy = PublishingSettings.objects.get(pk=1)
        self.assertEqual(policy.news_site_url, ORIGIN)
        self.assertFalse(policy.ingestion_paused)
        self.assertEqual(policy.daily_article_limit, 0)
        self.assertFalse(policy.require_review_for_automation)

    def test_build_configuration_only_changes_legacy_default(self):
        for previous, expected, changed in (
                ("https://www.fabrything.com", ORIGIN, True),
                ("https://www.fabrything.com/", ORIGIN, True),
                (ORIGIN, ORIGIN, False),
                ("https://custom.example.com", "https://custom.example.com", False)):
            policy = PublishingSettings.current()
            policy.news_site_url = previous
            policy.save()
            before = policy.updated_at
            output = StringIO()
            call_command("configure_news_domain", origin=ORIGIN, if_default=True, stdout=output)
            self.assertEqual(json.loads(output.getvalue()), {"news_site_url": expected, "changed": changed})
            policy.refresh_from_db()
            self.assertEqual(policy.news_site_url, expected)
            if not changed:
                self.assertEqual(policy.updated_at, before)

    def test_explicit_activation_can_replace_saved_custom_origin(self):
        policy = PublishingSettings.current()
        policy.news_site_url = "https://custom.example.com"
        policy.save()
        call_command("set_news_site", origin=ORIGIN, stdout=StringIO())
        policy.refresh_from_db()
        self.assertEqual(policy.news_site_url, ORIGIN)

    def test_database_error_does_not_disclose_connection_details(self):
        with patch("nobleseek.management.commands.set_news_site.PublishingSettings.locked",
                   side_effect=DatabaseError("password=private")):
            with self.assertRaises(CommandError) as raised:
                call_command("set_news_site", origin=ORIGIN)
        self.assertNotIn("private", str(raised.exception))


class PublishingCapacityTests(TestCase):
    @override_settings(AWS_ACCESS_KEY_ID="PRIVATE_ACCESS", AWS_ACESS_KEY_SECRET="PRIVATE_SECRET",
                       AWS_STORAGE_BUCKET_NAME="PRIVATE_BUCKET", AWS_S3_ENDPOINT_URL="https://private.invalid")
    def test_read_only_counts_storage_flags_and_no_secrets(self):
        PublishingSettings.objects.all().delete()
        Article.objects.create(headline="Private headline", body_html="Private body", status="PUBLISHED",
                               fb_post_url="https://facebook.com/private-post")
        Article.objects.create(headline="Private blog", body_html="Private body", content_type="BLOG")
        ImageBlob.objects.create(sha256="a" * 64, content_type="image/png", data=b"abc", byte_size=3)
        Products.objects.create(name="Private product", slug="private-product", sku="PRIVATE-SKU",
                                description="Private description", initial_buying_price=10,
                                initial_selling_price=20, status="ACTIVE")
        output = StringIO()
        call_command("publishing_capacity", stdout=output)
        raw = output.getvalue()
        data = json.loads(raw)
        self.assertEqual(data["counts"]["total"], 2)
        self.assertEqual(data["counts"]["news"], 1)
        self.assertEqual(data["counts"]["blog"], 1)
        self.assertEqual(data["counts"]["live_published"], 1)
        self.assertEqual(data["counts"]["with_recorded_facebook_link"], 1)
        self.assertEqual(data["database_images"], {"count": 1, "payload_bytes": 3})
        self.assertEqual(data["catalog"], {"total": 1, "active": 1})
        self.assertFalse(data["database"]["available"])
        self.assertTrue(data["storage_configuration"]["access_key_configured"])
        self.assertTrue(data["storage_configuration"]["secret_key_configured"])
        for secret in ("PRIVATE", "private.invalid", "facebook.com", "Private headline", "Private body"):
            self.assertNotIn(secret, raw)
        self.assertFalse(PublishingSettings.objects.exists())
        alias_output = StringIO()
        call_command("capacity_snapshot", stdout=alias_output)
        self.assertEqual(json.loads(alias_output.getvalue()), data)

    def test_capacity_failure_does_not_print_database_error(self):
        with patch("nobleseek.management.commands.publishing_capacity.Article.objects.aggregate",
                   side_effect=DatabaseError("private hostname")):
            with self.assertRaises(CommandError) as raised:
                call_command("publishing_capacity")
        self.assertNotIn("private", str(raised.exception))
