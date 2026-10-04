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

    def test_scheduled_future_hidden_until_due(self):
        from datetime import timedelta
        from django.utils import timezone
        f = Article.objects.create(
            headline="scheduled future story",
            body_html="<p>hi</p>",
            status=Article.Status.PUBLISHED,
            published_at=timezone.now() + timedelta(hours=2))
        c = APIClient()
        r = c.get(f"/api/store/nobleseek/articles/{f.slug}/")
        assert r.status_code == 404, r.content[:200]
        r2 = c.get("/api/store/nobleseek/articles/")
        slugs = [a["slug"] for a in r2.json()["results"]]
        assert f.slug not in slugs

    def test_popular_ordering(self):
        from django.utils import timezone
        low = Article.objects.create(
            headline="low views story", body_html="<p>hi</p>",
            status=Article.Status.PUBLISHED,
            published_at=timezone.now(), view_count=3)
        high = Article.objects.create(
            headline="high views story", body_html="<p>hi</p>",
            status=Article.Status.PUBLISHED,
            published_at=timezone.now(), view_count=999)
        c = APIClient()
        r = c.get("/api/store/nobleseek/articles/", {"popular": "1"})
        assert r.status_code == 200, r.content[:200]
        slugs = [a["slug"] for a in r.json()["results"]]
        assert slugs.index(high.slug) < slugs.index(low.slug)


class NobleSeekOverviewTests(TestCase):
    """Module overview for the News dashboard (staff-only)."""

    def test_overview_shape_and_numbers(self):
        from types import SimpleNamespace

        from rest_framework.test import APIRequestFactory, force_authenticate

        from nobleseek.views_admin import AdminNewsOverviewView
        Article.objects.create(
            headline="top story", body_html="<p>hi</p>",
            status=Article.Status.PUBLISHED, view_count=42)
        Article.objects.create(
            headline="needs review", body_html="<p>hi</p>",
            status=Article.Status.REVIEW)
        req = APIRequestFactory().get("/api/store/nobleseek/admin/overview/")
        force_authenticate(req, user=SimpleNamespace(
            id=1, role="Super Admin", is_authenticated=True,
            domain_user_id_id=1))
        r = AdminNewsOverviewView.as_view()(req)
        assert r.status_code == 200, r.data
        d = r.data["data"]
        assert d["kpis"]["published"] == 1
        assert d["kpis"]["total_views"] == 42
        assert len(d["series"]) == 14
        assert d["top_stories"][0]["view_count"] == 42
        assert d["alerts"]["review_queue"] == 1

    def test_overview_forbidden_for_customer(self):
        from types import SimpleNamespace

        from rest_framework.test import APIRequestFactory, force_authenticate

        from nobleseek.views_admin import AdminNewsOverviewView
        req = APIRequestFactory().get("/api/store/nobleseek/admin/overview/")
        force_authenticate(req, user=SimpleNamespace(
            id=2, role="Customer", is_authenticated=True,
            domain_user_id_id=2))
        r = AdminNewsOverviewView.as_view()(req)
        assert r.status_code == 403
