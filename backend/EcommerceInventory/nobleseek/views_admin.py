"""Admin NobleSeek API — staff-only via isPlatformStaff."""
from django.core.cache import cache
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.helpers import (CustomPageNumberPagination, isPlatformStaff,
                          renderResponse)
from rest_framework_simplejwt.authentication import JWTAuthentication
from storefront.permissions import IsPlatformStaff as StaffPerm

from .models import AdConfig, Article, Comment, FlatPage, NewsCategory, Poll, PollOption, PushCampaign, PushDevice, TrendKeyword
from .serializers import (AdConfigSerializer, ArticleAdminSerializer,
                          CommentSerializer, FlatPageSerializer,
                          NewsCategorySerializer, PollResultsSerializer,
                          PushCampaignSerializer, TrendKeywordSerializer)
from .services_ai import ai_draft_for_keyword
from .services_push import fcm_configured
from .services_trends import fetch_and_store


def _deny(request):
    return not (request.user and request.user.is_authenticated
                and isPlatformStaff(request.user))


class AdminArticleListCreateView(generics.ListCreateAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, StaffPerm]
    serializer_class = ArticleAdminSerializer
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        qs = Article.objects.select_related("category", "trend").order_by(
            "-updated_at")
        p = self.request.query_params
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("search"):
            from django.db.models import Q
            qs = qs.filter(Q(headline__icontains=p["search"]) |
                           Q(slug__icontains=p["search"]))
        return qs

    def perform_create(self, serializer):
        obj = serializer.save()
        cache.delete_many(["nobleseek:categories", "nobleseek:latest4"])


class AdminArticleDetailView(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, StaffPerm]
    serializer_class = ArticleAdminSerializer
    queryset = Article.objects.all()

    def perform_update(self, serializer):
        serializer.save()
        cache.delete_many(["nobleseek:categories", "nobleseek:latest4"])

    def perform_destroy(self, instance):
        instance.status = Article.Status.ARCHIVED
        instance.save()


class AdminCategoryListCreateView(generics.ListCreateAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, StaffPerm]
    serializer_class = NewsCategorySerializer
    pagination_class = None
    queryset = NewsCategory.objects.all().order_by("display_order")


class AdminCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Rename / reorder / deactivate sections from the Categories tab."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, StaffPerm]
    serializer_class = NewsCategorySerializer
    queryset = NewsCategory.objects.all()


class AdminTrendListView(generics.ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, StaffPerm]
    serializer_class = TrendKeywordSerializer
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        qs = TrendKeyword.objects.all().order_by("-fetched_at", "-traffic_score")
        p = self.request.query_params
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("geo"):
            qs = qs.filter(geo=p["geo"])
        return qs


class AdminTrendFetchView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, StaffPerm]

    def post(self, request):
        n = fetch_and_store(limit_per_geo=20)
        return renderResponse(data={"imported": n},
                              message=f"Fetched trends, {n} new keywords")


class AdminTrendCreateDraftView(APIView):
    """1-click: trend -> AI scaffold -> DRAFT article. Returns article id."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, StaffPerm]

    def post(self, request, pk):
        try:
            t = TrendKeyword.objects.get(pk=pk)
        except TrendKeyword.DoesNotExist:
            return Response({"message": "Trend not found"}, status=404)
        draft = ai_draft_for_keyword(t.keyword, t.geo, t.category_hint)
        headline = (draft["headlines"][0] if draft.get("headlines")
                    else t.keyword)[:255]
        article = Article.objects.create(
            trend=t, headline=headline, excerpt=draft.get("excerpt", "")[:300],
            body_html=draft.get("body_html", "<p>Write here…</p>"),
            status=Article.Status.DRAFT)
        t.status = TrendKeyword.Status.USED
        t.save(update_fields=["status"])
        return renderResponse(
            data={"article_id": article.pk, "slug": article.slug,
                  "headlines": draft.get("headlines", []),
                  "ai_generated": draft.get("ai_generated", False)},
            message="Draft created from trend")


class AdminTrendIgnoreView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, StaffPerm]

    def post(self, request, pk):
        TrendKeyword.objects.filter(pk=pk).update(status=TrendKeyword.Status.IGNORED)
        return renderResponse(data={"id": pk}, message="Trend ignored")


class AdminAdConfigView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, StaffPerm]

    def get(self, request):
        return renderResponse(data=AdConfigSerializer(AdConfig.get_solo()).data,
                              message="Ad config")

    def put(self, request):
        cfg = AdConfig.get_solo()
        ser = AdConfigSerializer(cfg, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return renderResponse(data=ser.data, message="Ad config saved")


class AdminNewsStatsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, StaffPerm]

    def get(self, request):
        from django.db.models import Sum
        return renderResponse(data={
            "drafts": Article.objects.filter(status=Article.Status.DRAFT).count(),
            "review": Article.objects.filter(status=Article.Status.REVIEW).count(),
            "published": Article.objects.filter(status=Article.Status.PUBLISHED).count(),
            "trends_new": TrendKeyword.objects.filter(status=TrendKeyword.Status.NEW).count(),
            "total_views": Article.objects.aggregate(s=Sum("view_count"))["s"] or 0,
        }, message="News stats")


class AdminTagsView(APIView):
    """Distinct tags with usage counts (tags live as JSON lists, so this
    aggregates in Python — fine at news-desk scale)."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, StaffPerm]

    def get(self, request):
        from collections import Counter
        status = request.query_params.get("status", "")
        qs = Article.objects.exclude(status=Article.Status.ARCHIVED)
        if status:
            qs = qs.filter(status=status)
        counter = Counter()
        for tags in qs.values_list("tags", flat=True):
            for t in (tags or []):
                t = str(t).strip()
                if t:
                    counter[t] += 1
        data = [{"tag": t, "count": n}
                for t, n in counter.most_common(100)]
        return renderResponse(data=data, message="Tags")


class AdminFlatPageListCreateView(generics.ListCreateAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, StaffPerm]
    serializer_class = FlatPageSerializer
    pagination_class = None
    queryset = FlatPage.objects.all().order_by("slug")


class AdminFlatPageDetailView(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, StaffPerm]
    serializer_class = FlatPageSerializer
    queryset = FlatPage.objects.all()
    lookup_field = "slug"


class AdminCommentListView(generics.ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, StaffPerm]
    serializer_class = CommentSerializer
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        qs = Comment.objects.select_related("article").order_by("-flags", "-created_at")
        p = self.request.query_params
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        return qs


class AdminCommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, StaffPerm]
    serializer_class = CommentSerializer
    queryset = Comment.objects.all()


class AdminPushDeviceListView(generics.ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, StaffPerm]
    pagination_class = CustomPageNumberPagination

    def get(self, request):
        qs = PushDevice.objects.filter(is_active=True)
        topic = request.query_params.get("topic", "")
        if topic:
            # SQLite JSON contains works on serialized lists for exact items.
            qs = qs.filter(topics__contains=topic)
        return renderResponse(data={
            "count": qs.count(),
            "configured": fcm_configured(),
        }, message="Push subscribers")


class AdminPushSendView(APIView):
    """Compose + send a breaking-news push. Logged as a campaign; without
    FCM_SERVER_KEY the run is recorded as skipped, never an exception."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, StaffPerm]

    def post(self, request):
        from .services_push import send_push
        title = str(request.data.get("title", ""))[:120].strip()
        body = str(request.data.get("body", ""))[:300].strip()
        url = str(request.data.get("url", ""))[:500]
        topic = str(request.data.get("topic", "")).strip()
        if not title or not body:
            return Response({"message": "Title and body required"}, status=400)
        qs = PushDevice.objects.filter(is_active=True)
        if topic:
            qs = qs.filter(topics__contains=topic)
        devices = list(qs)
        result = send_push(devices, title, body, url)
        camp = PushCampaign.objects.create(
            title=title, body=body, url=url, audience=len(devices),
            sent=result["sent"], failed=result["failed"],
            skipped=result["skipped"], note=result.get("note", ""))
        return renderResponse(data=PushCampaignSerializer(camp).data,
                              message="Push campaign recorded")


class AdminPushCampaignListView(generics.ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, StaffPerm]
    serializer_class = PushCampaignSerializer
    pagination_class = CustomPageNumberPagination
    queryset = PushCampaign.objects.all().order_by("-created_at")


class AdminPollListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, StaffPerm]

    def get(self, request):
        polls = Poll.objects.prefetch_related("options").order_by("-created_at")
        return renderResponse(
            data=PollResultsSerializer(
                [p.results() for p in polls], many=True).data,
            message="Polls")

    def post(self, request):
        question = str(request.data.get("question", ""))[:255].strip()
        options = [str(o)[:200].strip() for o in request.data.get("options", [])]
        options = [o for o in options if o][:6]
        if not question or len(options) < 2:
            return Response(
                {"message": "Question + at least 2 options required"},
                status=400)
        poll = Poll.objects.create(
            question=question,
            is_active=bool(request.data.get("is_active", True)))
        for i, text in enumerate(options):
            PollOption.objects.create(poll=poll, text=text, display_order=i)
        return renderResponse(data=poll.results(), message="Poll created",
                              status=201)


class AdminPollDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, StaffPerm]

    def _get(self, pk):
        try:
            return Poll.objects.prefetch_related("options").get(pk=pk)
        except Poll.DoesNotExist:
            return None

    def get(self, request, pk):
        poll = self._get(pk)
        if not poll:
            return Response({"message": "Poll not found"}, status=404)
        return renderResponse(data=poll.results(), message="Poll")

    def patch(self, request, pk):
        poll = self._get(pk)
        if not poll:
            return Response({"message": "Poll not found"}, status=404)
        if "is_active" in request.data:
            poll.is_active = bool(request.data["is_active"])
        if "question" in request.data and str(request.data["question"]).strip():
            poll.question = str(request.data["question"])[:255].strip()
        poll.save()
        return renderResponse(data=poll.results(), message="Poll updated")

    def delete(self, request, pk):
        deleted, _ = Poll.objects.filter(pk=pk).delete()
        if not deleted:
            return Response({"message": "Poll not found"}, status=404)
        return renderResponse(data={"id": pk}, message="Poll deleted")


class AdminNewsOverviewView(APIView):
    """Module overview for the News dashboard: desk KPIs, 14/30-day
    publishing activity, top stories by views, and desk alerts."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, StaffPerm]

    def get(self, request):
        from datetime import timedelta

        from django.db.models import Count, Sum
        from django.db.models.functions import TruncDate
        try:
            days = int(request.query_params.get("days", 14))
        except (TypeError, ValueError):
            days = 14
        days = days if days in (7, 14, 30) else 14
        now = timezone.now()
        since = now - timedelta(days=days)
        rows = (
            Article.objects.filter(status=Article.Status.PUBLISHED,
                                   published_at__gte=since)
            .annotate(day=TruncDate("published_at"))
            .values("day").annotate(n=Count("id")).order_by("day")
        )
        by_day = {r["day"]: r["n"] for r in rows}
        series = []
        for i in range(days - 1, -1, -1):
            d = (now - timedelta(days=i)).date()
            series.append({"day": d.isoformat(), "total": 0.0,
                           "count": by_day.get(d, 0)})
        empty_sections = [
            c.name for c in NewsCategory.objects.filter(is_active=True)
            if not Article.objects.filter(
                category=c, status=Article.Status.PUBLISHED).exists()
        ]
        from accounts.models import Users
        from core.helpers import PLATFORM_STAFF_ROLES
        return renderResponse(data={
            "kpis": {
                "published": Article.objects.filter(
                    status=Article.Status.PUBLISHED).count(),
                "drafts": Article.objects.filter(
                    status=Article.Status.DRAFT).count(),
                "review": Article.objects.filter(
                    status=Article.Status.REVIEW).count(),
                "total_views": Article.objects.aggregate(
                    s=Sum("view_count"))["s"] or 0,
                "trends_new": TrendKeyword.objects.filter(
                    status=TrendKeyword.Status.NEW).count(),
                "staff": Users.objects.filter(role__in=PLATFORM_STAFF_ROLES).count(),
            },
            "series": series,
            "top_stories": list(
                Article.objects.filter(status=Article.Status.PUBLISHED)
                .order_by("-view_count")
                .values("headline", "slug", "view_count",
                        "published_at")[:5]
            ),
            "alerts": {
                "review_queue": Article.objects.filter(
                    status=Article.Status.REVIEW).count(),
                "scheduled": Article.objects.filter(
                    status=Article.Status.PUBLISHED,
                    published_at__gt=now).count(),
                "trends_new": TrendKeyword.objects.filter(
                    status=TrendKeyword.Status.NEW).count(),
                "pending_comments": Comment.objects.filter(
                    status=Comment.Status.PENDING).count(),
                "flagged_comments": Comment.objects.filter(flags__gt=0).count(),
                "empty_sections": empty_sections,
            },
        }, message="News overview")
