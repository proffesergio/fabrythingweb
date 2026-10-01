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

from .models import AdConfig, Article, NewsCategory, TrendKeyword
from .serializers import (AdConfigSerializer, ArticleAdminSerializer,
                          NewsCategorySerializer, TrendKeywordSerializer)
from .services_ai import ai_draft_for_keyword
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
