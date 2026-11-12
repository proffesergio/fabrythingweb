import json
from html import escape
from django.http import HttpResponse, Http404
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from nobleseek.models import Article
from nobleseek.serializers import ArticleListSerializer
from .journal import ORIGIN, journal_data, journal_json_ld
from .journal_models import TopicCluster


class JournalTopicsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(list(TopicCluster.objects.filter(active=True).values('id', 'name', 'slug', 'parent_id', 'level', 'description').order_by('level', 'name')[:250]))


class JournalRelatedView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        current = Article.objects.filter(slug=slug, content_type='BLOG', status='PUBLISHED', published_at__lte=timezone.now()).first()
        data = journal_data(current) if current else None
        if not data:
            return Response([])
        cluster = current.journal.cluster
        cluster_ids = [cluster.pk] if cluster else []
        if cluster and cluster.parent_id:
            cluster_ids.extend(TopicCluster.objects.filter(parent_id=cluster.parent_id, active=True).values_list('id', flat=True))
        related = Article.objects.filter(content_type='BLOG', status='PUBLISHED', published_at__lte=timezone.now(), journal__cluster_id__in=cluster_ids).exclude(pk=current.pk).select_related('category')[:4]
        return Response(ArticleListSerializer(related, many=True, context={'request': request}).data)


def journal_document(request, slug):
    """Indexable HTML at the canonical route; no crawler-only alternate content."""
    article = Article.objects.filter(slug=slug, content_type='BLOG', status='PUBLISHED', published_at__lte=timezone.now()).first()
    if not article:
        raise Http404('Article not found')
    data = journal_data(article)
    schema = json.dumps(journal_json_ld(article), ensure_ascii=False).replace('<', '\\u003c')
    title, description, url = map(escape, (article.seo_title or article.headline, article.seo_description or article.excerpt, article.get_canonical_url()))
    disclosure = '<aside aria-label="Affiliate disclosure">' + escape(data['disclosure']) + '</aside>' if data else ''
    # body_html is sanitized on all writer paths; legacy articles use the same sanitizer.
    from nobleseek.sanitization import sanitize_article_html
    body = sanitize_article_html(article.body_html)
    hero = f'<img src="{escape(article.hero_image, quote=True)}" alt="{escape(article.hero_image_alt, quote=True)}" width="1200" height="675" fetchpriority="high">' if article.hero_image else ''
    image_url = article.hero_image or ORIGIN + '/fabrything-horizontal-light.png'
    image_meta = '<meta property="og:image" content="' + escape(image_url, quote=True) + '"><meta name="twitter:image" content="' + escape(image_url, quote=True) + '"><meta property="og:site_name" content="Fabrything"><meta property="article:published_time" content="' + article.published_at.isoformat() + '">'
    sources = '<section aria-label="Sources"><h2>Sources & further reading</h2><ul>' + ''.join('<li><a href="' + escape(x['url'], quote=True) + '" rel="noopener">' + escape(x['title']) + '</a></li>' for x in data['sources']) + '</ul></section>' if data else ''
    related = Article.objects.filter(content_type='BLOG', status='PUBLISHED', published_at__lte=timezone.now(), journal__cluster_id=article.journal.cluster_id).exclude(pk=article.pk).only('headline', 'slug')[:4] if data else []
    related_html = '<aside aria-label="Related guides"><h2>Keep reading</h2>' + ''.join('<p><a href="/blog/' + escape(x.slug, quote=True) + '">' + escape(x.headline) + '</a></p>' for x in related) + '</aside>' if related else ''
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} — Fabrything Journal</title><meta name="description" content="{description}"><link rel="canonical" href="{url}"><meta property="og:title" content="{title}"><meta property="og:description" content="{description}"><meta property="og:url" content="{url}"><meta property="og:type" content="article">{image_meta}<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{title}"><meta name="twitter:description" content="{description}"><script type="application/ld+json">{schema}</script><style>body{{margin:0;background:#f8fafc;color:#0f172a;font:18px/1.8 system-ui}}header,main,footer{{max-width:960px;margin:auto;padding:24px}}nav a{{margin-right:20px}}a{{color:#3730a3}}img{{max-width:100%;height:auto;aspect-ratio:16/9;object-fit:contain}}article{{background:white;padding:32px;border-radius:16px}}aside{{padding:16px;background:#f1f5f9}}table{{width:100%;border-collapse:collapse}}td,th{{padding:12px;border:1px solid #e2e8f0}}h1{{line-height:1.2}}@media(max-width:600px){{article{{padding:16px}}}}</style></head><body><header><a href="/" aria-label="Fabrything home"><img src="/fabrything-horizontal-light.png" alt="Fabrything" width="180" height="36" style="width:180px;height:36px;aspect-ratio:auto"></a><nav aria-label="Main"><a href="/shop">Shop</a><a href="/blog">Journal</a><a href="/about">About</a><a href="/contact">Contact</a></nav></header><main><nav aria-label="Breadcrumb"><a href="/">Home</a> / <a href="/blog">Journal</a> / {escape(article.headline)}</nav><article><header><h1>{escape(article.effective_headline)}</h1><p>{escape(article.excerpt)}</p><p>Fabrything Editorial · Updated {article.updated_at.date().isoformat()}</p></header>{disclosure}{hero}{body}{sources}{related_html}</article></main><footer><a href="/privacy">Privacy</a> · <a href="/terms">Terms</a> · <a href="/disclosure">Affiliate & advertising disclosure</a></footer></body></html>'''
    response = HttpResponse(html)
    response['Cache-Control'] = 'public, max-age=0, s-maxage=60'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


def journal_robots(request):
    return HttpResponse('User-agent: *\nAllow: /\nDisallow: /admin/\nDisallow: /account/\nDisallow: /checkout/\nDisallow: /api/\nSitemap: ' + ORIGIN + '/sitemap.xml\n', content_type='text/plain')
