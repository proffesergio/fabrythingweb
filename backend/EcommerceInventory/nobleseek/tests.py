"""Smoke tests for NobleSeek public + staff gating."""
from django.test import TestCase
from rest_framework.test import APIClient

from nobleseek.models import Article, NewsCategory


class NobleSeekPublicTests(TestCase):
    def setUp(self):
        self.cat = NewsCategory.objects.create(name="Tech", slug="tech")
        self.art = Article.objects.create(
            category=self.cat, headline="Test headline iPhone 17 BD",
            excerpt="excerpt", body_html="<p>" + ("word " * 400) + "</p>",
            status=Article.Status.PUBLISHED)

    def test_list_and_detail(self):
        c = APIClient()
        r = c.get("/api/store/nobleseek/articles/")
        assert r.status_code == 200, r.content[:300]
        r2 = c.get(f"/api/store/nobleseek/articles/{self.art.slug}/")
        assert r2.status_code == 200, r2.content[:300]
        assert r2.json()["data"]["read_time_minutes"] >= 1

    def test_draft_hidden(self):
        d = Article.objects.create(headline="draft hidden",
                                   body_html="<p>hi</p>",
                                   status=Article.Status.DRAFT)
        c = APIClient()
        r = c.get(f"/api/store/nobleseek/articles/{d.slug}/")
        assert r.status_code == 404
