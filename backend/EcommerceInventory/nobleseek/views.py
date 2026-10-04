"""Public NobleSeek API — AllowAny, published-only, cached lists."""
from django.core.cache import cache
from django.db import models, transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.helpers import CustomPageNumberPagination, renderResponse

from .models import AdConfig, Article, Comment, FlatPage, NewsCategory, Poll, PushDevice
from .serializers import (AdConfigSerializer, ArticleDetailSerializer,
                          ArticleListSerializer, CommentSerializer,
                          FlatPageSerializer, NewsCategorySerializer,
                          PollResultsSerializer, PushDeviceSerializer)


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


class FlatPagePublicView(APIView):
    """Editable trust pages. Inactive/missing slug → 404 and the portal
    falls back to its built-in copy (never a blank page)."""
    permission_classes = [AllowAny]

    def get(self, request, slug):
        try:
            page = FlatPage.objects.get(slug=slug, is_active=True)
        except FlatPage.DoesNotExist:
            return Response({"message": "Page not found"}, status=404)
        return renderResponse(data=FlatPageSerializer(page).data,
                              message="Info page")


class CommentListCreateView(APIView):
    """GET ?article=<id> → approved comments only. POST creates PENDING
    (desk approves; never public on arrival — spam safety)."""
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            article_id = int(request.query_params.get("article", 0))
        except (TypeError, ValueError):
            return Response({"message": "article id required"}, status=400)
        qs = Comment.objects.filter(
            article_id=article_id,
            status=Comment.Status.APPROVED).order_by("-created_at")[:100]
        return renderResponse(data=CommentSerializer(qs, many=True).data,
                              message="Comments")

    def post(self, request):
        name = str(request.data.get("name", "")).strip()[:80]
        text = str(request.data.get("text", "")).strip()[:500]
        try:
            article_id = int(request.data.get("article", 0))
        except (TypeError, ValueError):
            article_id = 0
        if len(name) < 2 or len(text) < 2:
            return Response({"message": "Name and comment required"}, status=400)
        if not _visible_qs().filter(pk=article_id).exists():
            return Response({"message": "Article not found"}, status=404)
        # Light spam guard: one comment per 30s per IP.
        ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() \
            or request.META.get("REMOTE_ADDR", "")
        key = f"nobleseek:comment:{ip}"
        if cache.get(key):
            return Response(
                {"message": "A little slower — please wait a few seconds"},
                status=429)
        cache.set(key, 1, 30)
        c = Comment.objects.create(article_id=article_id, name=name, text=text)
        return renderResponse(data=CommentSerializer(c).data,
                              message="Received — visible after review", status=201)


class CommentFlagView(APIView):
    """Reader reports a comment; moderation queue sorts by flags."""
    permission_classes = [AllowAny]

    def post(self, request, pk):
        updated = Comment.objects.filter(pk=pk).update(
            flags=models.F("flags") + 1)
        if not updated:
            return Response({"message": "Comment not found"}, status=404)
        return renderResponse(data={"id": pk}, message="Reported — thanks")


class PollListView(APIView):
    """Active polls with live aggregates (no voter identity leaks)."""
    permission_classes = [AllowAny]

    def get(self, request):
        polls = Poll.objects.filter(is_active=True).prefetch_related("options")[:5]
        data = PollResultsSerializer([p.results() for p in polls], many=True).data
        return renderResponse(data=data, message="Active polls")


class PollVoteView(APIView):
    """One vote per browser (client UUID). Repeat votes → 400, not silent."""
    permission_classes = [AllowAny]

    def post(self, request, pk):
        try:
            poll = Poll.objects.prefetch_related("options").get(
                pk=pk, is_active=True)
        except Poll.DoesNotExist:
            return Response({"message": "Poll closed"}, status=404)
        try:
            option_id = int(request.data.get("option_id", 0))
        except (TypeError, ValueError):
            option_id = 0
        session_key = str(request.data.get("session_key", ""))[:64]
        if not session_key or not poll.options.filter(pk=option_id).exists():
            return Response({"message": "Pick an option"}, status=400)
        from django.db import IntegrityError
        from .models import PollVote
        try:
            with transaction.atomic():
                PollVote.objects.create(poll=poll, option_id=option_id,
                                        session_key=session_key)
        except IntegrityError:
            return Response({"message": "Already voted"}, status=400)
        return renderResponse(data=poll.results(), message="Vote counted")


class PushSubscribeView(APIView):
    """Store/refresh a push token (app today, web tomorrow). Idempotent."""
    permission_classes = [AllowAny]

    def post(self, request):
        token = str(request.data.get("token", ""))[:255].strip()
        if not token:
            return Response({"message": "token required"}, status=400)
        platform = str(request.data.get("platform", "android"))[:16]
        topics = request.data.get("topics", [])
        if not isinstance(topics, list):
            topics = []
        PushDevice.objects.update_or_create(
            token=token,
            defaults={"platform": platform, "topics": topics[:10],
                      "is_active": True})
        return renderResponse(data={"subscribed": True},
                              message="Subscribed to breaking alerts")
