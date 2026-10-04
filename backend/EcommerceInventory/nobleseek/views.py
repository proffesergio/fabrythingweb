"""Public NobleSeek API — AllowAny, published-only, cached lists."""
from django.core.cache import cache
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.helpers import CustomPageNumberPagination, renderResponse

from .models import AdConfig, Article, NewsCategory
from .serializers import (AdConfigSerializer, ArticleDetailSerializer,
                          ArticleListSerializer, NewsCategorySerializer)


def _visible_qs():
    """Published AND already live. Editors can schedule a future
    published_at — those stay hidden until the timestamp passes."""
    return Article.objects.filter(status=Article.Status.PUBLISHED,
                                  published_at__lte=timezone.now())


class NewsCategoryListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = NewsCategorySerializer
    pagination_class = None

    def get_queryset(self):
        return NewsCategory.objects.filter(is_active=True).annotate(
            article_count=Count("articles",
                                filter=Q(articles__status=Article.Status.PUBLISHED)))

    def list(self, request, *args, **kwargs):
        data = cache.get("nobleseek:categories")
        if data is None:
            data = self.get_serializer(self.get_queryset(), many=True).data
            cache.set("nobleseek:categories", data, 600)
        return renderResponse(data=data, message="News categories")


class ArticleListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ArticleListSerializer
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        qs = _visible_qs().select_related("category")
        p = self.request.query_params
        if p.get("popular") == "1":
            qs = qs.order_by("-view_count", "-published_at")
        else:
            qs = qs.order_by("-published_at", "-created_at")
        if p.get("category"):
            qs = qs.filter(category__slug=p["category"])
        if p.get("search"):
            # NOTE: tags is a JSONField — __icontains on JSONB is backend
            # fragile (can 500 on Postgres), so search text columns only.
            qs = qs.filter(Q(headline__icontains=p["search"]) |
                           Q(headline_bn__icontains=p["search"]) |
                           Q(excerpt__icontains=p["search"]))
        if p.get("featured") == "1":
            qs = qs.filter(is_featured=True)
        if p.get("breaking") == "1":
            qs = qs.filter(is_breaking=True)
        return qs


class ArticleDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        try:
            a = _visible_qs().select_related("category").get(slug=slug)
        except Article.DoesNotExist:
            return Response({"message": "Article not found"}, status=404)
        # lightweight view counter (1 per 30 min per IP via cache)
        ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() \
            or request.META.get("REMOTE_ADDR", "")
        key = f"nobleseek:view:{a.pk}:{ip}"
        if not cache.get(key):
            Article.objects.filter(pk=a.pk).update(view_count=a.view_count + 1)
            a.view_count += 1
            cache.set(key, 1, 1800)
        ser = ArticleDetailSerializer(a, context={"request": request})
        return renderResponse(data=ser.data, message="Article detail")


class RelatedArticlesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        try:
            cur = _visible_qs().select_related("category").get(slug=slug)
        except Article.DoesNotExist:
            return Response({"message": "Article not found"}, status=404)
        qs = _visible_qs().exclude(pk=cur.pk)
        if cur.category_id:
            same = list(qs.filter(category_id=cur.category_id)
                        .order_by("-published_at")[:4])
        else:
            same = []
        others = list(qs.exclude(pk__in=[x.pk for x in same])
                      .order_by("-published_at")[: max(0, 4 - len(same))])
        ser = ArticleListSerializer(same + others, many=True,
                                    context={"request": request})
        return renderResponse(data=ser.data, message="Related articles")


class LatestStripView(APIView):
    """Tiny payload for shop homepage strip (4 latest)."""
    permission_classes = [AllowAny]

    def get(self, request):
        data = cache.get("nobleseek:latest4")
        if data is None:
            qs = (_visible_qs()
                  .select_related("category").order_by("-published_at")[:4])
            data = ArticleListSerializer(qs, many=True,
                                             context={"request": request}).data
            cache.set("nobleseek:latest4", data, 300)
        return renderResponse(data=data, message="Latest news")


class NewsSitemapView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        base = f"{request.scheme}://{request.get_host()}"
        urls = [f"{base}/nobleseek",
                f"{base}/nobleseek/about",
                f"{base}/nobleseek/contact"]
        for a in _visible_qs().order_by(
                "-published_at")[:500].only("slug", "updated_at"):
            urls.append({"loc": f"{base}/nobleseek/{a.slug}",
                         "lastmod": a.updated_at.date().isoformat()})
        return renderResponse(data={"urls": urls}, message="News sitemap")


class NewsRssView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        base = f"{request.scheme}://{request.get_host()}"
        items = ArticleDetailSerializer(
            _visible_qs()
            .select_related("category").order_by("-published_at")[:20],
            many=True, context={"request": request}).data
        return renderResponse(data={"site": base, "items": items},
                              message="News RSS")


class AdConfigPublicView(APIView):
    """Frontend reads slot ids + density flags (no secrets)."""
    permission_classes = [AllowAny]

    def get(self, request):
        cfg = AdConfig.get_solo()
        return renderResponse(data=AdConfigSerializer(cfg).data,
                              message="Ad config")
