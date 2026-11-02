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

    def test_relative_hero_image_served_absolute(self):
        """DB-blob uploads return relative /api/media/<sha>/ paths, which are
        unloadable on the storefront origin — public serializers must make
        them absolute (same contract as catalog images)."""
        a = Article.objects.create(
            headline="relative hero story", body_html="<p>hi</p>",
            hero_image="/api/media/abc123/", status=Article.Status.PUBLISHED)
        c = APIClient()
        r = c.get("/api/store/nobleseek/articles/")
        assert r.status_code == 200, r.content[:200]
        row = [x for x in r.json()["results"] if x["slug"] == a.slug][0]
        assert row["hero_image"].startswith("http"), row["hero_image"]
        assert row["hero_image"].endswith("/api/media/abc123/")
        r2 = c.get(f"/api/store/nobleseek/articles/{a.slug}/")
        assert r2.status_code == 200, r2.content[:200]
        assert r2.json()["data"]["hero_image"].startswith("http")

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


class NobleSeekPagesCommentsPollsPushTests(TestCase):
    def test_flatpage_public_and_404(self):
        from nobleseek.models import FlatPage
        FlatPage.objects.create(slug="about", title="About", body_html="<p>hi</p>")
        c = APIClient()
        assert c.get("/api/store/nobleseek/pages/about/").status_code == 200
        assert c.get("/api/store/nobleseek/pages/nope/").status_code == 404

    def test_comments_pending_until_approved(self):
        from nobleseek.models import Comment
        art = Article.objects.create(
            headline="comment story", body_html="<p>hi</p>",
            status=Article.Status.PUBLISHED)
        c = APIClient()
        r = c.post("/api/store/nobleseek/comments/",
                   {"article": art.pk, "name": "Rahim", "text": "nice"})
        assert r.status_code == 201, r.content[:200]
        assert r.json()["data"]["status"] == "PENDING"
        # Not public before approval…
        r2 = c.get("/api/store/nobleseek/comments/", {"article": art.pk})
        assert r2.json()["data"] == []
        # …flag + approve via ORM (admin path covered below), then visible.
        Comment.objects.filter(pk=r.json()["data"]["id"]).update(
            status=Comment.Status.APPROVED)
        r3 = c.get("/api/store/nobleseek/comments/", {"article": art.pk})
        assert len(r3.json()["data"]) == 1
        # Flagging works on any comment.
        cid = r.json()["data"]["id"]
        assert c.post(f"/api/store/nobleseek/comments/{cid}/flag/").status_code == 200
        assert Comment.objects.get(pk=cid).flags == 1

    def test_comment_validation(self):
        art = Article.objects.create(
            headline="validation story", body_html="<p>hi</p>",
            status=Article.Status.PUBLISHED)
        c = APIClient()
        assert c.post("/api/store/nobleseek/comments/",
                      {"article": art.pk, "name": "x", "text": "y"}).status_code == 400
        assert c.post("/api/store/nobleseek/comments/",
                      {"article": 99999, "name": "ok", "text": "fine"}).status_code == 404

    def test_poll_vote_once(self):
        from nobleseek.models import Poll, PollOption
        from nobleseek.views_admin import AdminPollListCreateView
        from rest_framework.test import APIRequestFactory, force_authenticate
        from types import SimpleNamespace
        staff = SimpleNamespace(id=1, role="Super Admin",
                                is_authenticated=True, domain_user_id_id=1)
        req = APIRequestFactory().post(
            "/api/store/nobleseek/admin/polls/",
            {"question": "Best?", "options": ["A", "B"]}, format="json")
        force_authenticate(req, user=staff)
        r = AdminPollListCreateView.as_view()(req)
        assert r.status_code == 201, r.data
        pid = r.data["data"]["id"]
        c = APIClient()
        opt = PollOption.objects.filter(poll_id=pid).first().pk
        v1 = c.post(f"/api/store/nobleseek/polls/{pid}/vote/",
                    {"option_id": opt, "session_key": "s1"})
        assert v1.status_code == 200, v1.content[:200]
        assert v1.json()["data"]["total"] == 1
        v2 = c.post(f"/api/store/nobleseek/polls/{pid}/vote/",
                    {"option_id": opt, "session_key": "s1"})
        assert v2.status_code == 400
        assert Poll.objects.get(pk=pid).results()["total"] == 1

    def test_push_subscribe_and_send_skipped_without_key(self):
        from nobleseek.models import PushCampaign, PushDevice
        c = APIClient()
        r = c.post("/api/store/nobleseek/push/subscribe/",
                   {"token": "tok123", "platform": "android"})
        assert r.status_code == 200, r.content[:200]
        assert PushDevice.objects.filter(token="tok123").exists()
        # idempotent re-subscribe
        c.post("/api/store/nobleseek/push/subscribe/", {"token": "tok123"})
        assert PushDevice.objects.filter(token="tok123").count() == 1
        # Admin send without FCM key records a skipped campaign, never 500.
        from nobleseek.views_admin import AdminPushSendView
        from rest_framework.test import APIRequestFactory, force_authenticate
        from types import SimpleNamespace
        req = APIRequestFactory().post(
            "/api/store/nobleseek/admin/push/send/",
            {"title": "T", "body": "B"}, format="json")
        force_authenticate(req, user=SimpleNamespace(
            id=1, role="Super Admin", is_authenticated=True,
            domain_user_id_id=1))
        r2 = AdminPushSendView.as_view()(req)
        assert r2.status_code == 200, r2.data
        camp = PushCampaign.objects.latest("created_at")
        assert camp.skipped == 1 and camp.sent == 0

    def test_subcategory_filter(self):
        parent = NewsCategory.objects.create(name="Sports", slug="sports")
        child = NewsCategory.objects.create(
            name="Cricket", slug="cricket", parent=parent)
        Article.objects.create(
            category=child, headline="cricket fever", body_html="<p>hi</p>",
            status=Article.Status.PUBLISHED)
        c = APIClient()
        r = c.get("/api/store/nobleseek/articles/", {"category": "cricket"})
        assert r.status_code == 200
        assert [a["slug"] for a in r.json()["results"]] != []
        # admin serializer exposes the parent link
        from nobleseek.serializers import NewsCategorySerializer
        assert NewsCategorySerializer(child).data["parent"] == parent.pk


class NobleSeekCategorySafetyTests(TestCase):
    """Deleting a referenced section must fail; the restore endpoint must
    bring back defaults without touching articles."""

    def _staff(self):
        from types import SimpleNamespace

        from rest_framework.test import APIRequestFactory, force_authenticate
        req = APIRequestFactory().get("/")
        force_authenticate(req, user=SimpleNamespace(
            id=1, role="Super Admin", is_authenticated=True,
            domain_user_id_id=1))
        return req

    def test_delete_blocked_while_referenced(self):
        from nobleseek.views_admin import AdminCategoryDetailView
        cat = NewsCategory.objects.create(name="Sports", slug="sports")
        Article.objects.create(
            category=cat, headline="in sports", body_html="<p>hi</p>",
            status=Article.Status.PUBLISHED)
        req = self._staff()
        req.method = "DELETE"
        r = AdminCategoryDetailView.as_view()(req, pk=cat.pk)
        assert r.status_code == 400, r.data
        assert NewsCategory.objects.filter(pk=cat.pk).exists()

    def test_delete_empty_category_allowed(self):
        from nobleseek.views_admin import AdminCategoryDetailView
        cat = NewsCategory.objects.create(name="Empty", slug="empty")
        req = self._staff()
        req.method = "DELETE"
        r = AdminCategoryDetailView.as_view()(req, pk=cat.pk)
        assert r.status_code == 204, r.status_code
        assert not NewsCategory.objects.filter(pk=cat.pk).exists()

    def test_restore_recreates_defaults_idempotently(self):
        from nobleseek.models import FlatPage
        from nobleseek.views_admin import AdminCategoryRestoreView
        assert NewsCategory.objects.count() == 0
        req = self._staff()
        req.method = "POST"
        r = AdminCategoryRestoreView.as_view()(req)
        assert r.status_code == 200, r.data
        assert NewsCategory.objects.count() == 16
        assert FlatPage.objects.count() == 5
        # second run changes nothing, articles untouched
        art = Article.objects.create(
            headline="kept", body_html="<p>hi</p>",
            status=Article.Status.DRAFT)
        r2 = AdminCategoryRestoreView.as_view()(req)
        assert r2.status_code == 200
        assert NewsCategory.objects.count() == 16
        assert Article.objects.filter(pk=art.pk).exists()
