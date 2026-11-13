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
        return Response([{'id': t.pk, 'name': t.name, 'slug': t.slug, 'parent_id': t.parent_id, 'level': t.level, 'description': t.description} for t in sorted(public_topics(), key=lambda t: (t.level, t.name))[:250]])


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


def visible_guides():
    return Article.objects.filter(content_type='BLOG', status='PUBLISHED', published_at__lte=timezone.now()).order_by('-published_at', '-id')


def topic_ids(cluster):
    ids, frontier = [cluster.pk], [cluster.pk]
    for _ in range(4):
        frontier = list(TopicCluster.objects.filter(parent_id__in=frontier, active=True).values_list('id', flat=True))
        ids.extend(frontier)
    return ids


def public_topics():
    # Include ancestors of populated topics, never empty/future/review-only silos.
    used = set(visible_guides().exclude(journal__cluster=None).values_list('journal__cluster_id', flat=True))
    nodes = {t.pk: t for t in TopicCluster.objects.filter(active=True)}
    for pk in list(used):
        node, seen = nodes.get(pk), set()
        while node and node.pk not in seen:
            seen.add(node.pk)
            used.add(node.pk)
            node = nodes.get(node.parent_id)
    return [t for t in nodes.values() if t.pk in used]


def journal_document(request, slug):
    from django.shortcuts import render
    from .journal import guide_contents
    from nobleseek.sanitization import sanitize_article_html
    import re
    article = visible_guides().filter(slug=slug).first()
    if not article:
        raise Http404('Article not found')
    data = journal_data(article)
    related = visible_guides().filter(journal__cluster_id=article.journal.cluster_id).exclude(pk=article.pk)[:3] if data else []
    context = {'article': article, 'data': data, 'title': article.seo_title or article.effective_headline,
        'description': article.seo_description or article.excerpt, 'canonical': article.get_canonical_url(),
        'image_url': article.hero_image or ORIGIN + '/fabrything-horizontal-light.png',
        'schema': json.dumps(journal_json_ld(article), ensure_ascii=False).replace('<', '\\u003c'),
        'language': 'bn' if re.search(r'[\u0980-\u09ff]', article.effective_headline) else 'en',
        'body': sanitize_article_html(article.body_html), 'related': related,
        'contents': guide_contents(data['blocks']) if data else [],
        'intent': data['intent'].replace('_', ' ') if data else 'Products & everyday life',
        'disclosure': data['disclosure'] if data else 'This guide may include affiliate links. We may earn a commission from purchases. Check the destination website for the updated price.',
        'hero': article.hero_image and not (data and any(b.get('src') == article.hero_image for b in data['blocks']))}
    response = render(request, 'storefront/journal_document.html', context)
    response['Cache-Control'] = 'public, max-age=0, s-maxage=60'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


def journal_archive_document(request, topic=None):
    from django.shortcuts import render, get_object_or_404
    from urllib.parse import urlencode
    from .journal_contract import INTENTS
    cluster = get_object_or_404(TopicCluster, slug=topic, active=True) if topic else None
    qs = visible_guides()
    if cluster:
        qs = qs.filter(journal__cluster_id__in=topic_ids(cluster))
    intent = request.GET.get('intent', '')
    if intent:
        if intent not in INTENTS:
            raise Http404('Unknown guide format')
        qs = qs.filter(journal__intent=intent)
    try:
        page = max(1, min(10000, int(request.GET.get('page', '1'))))
    except ValueError:
        raise Http404('Invalid page')
    batch = list(qs[(page-1)*12:page*12+1])
    if page > 1 and not batch:
        raise Http404('Page not found')
    path = '/blog/topic/' + topic if topic else '/blog'
    def link(number):
        params = {'page': number} if number > 1 else {}
        if intent:
            params['intent'] = intent
        return path + ('?' + urlencode(params) if params else '')
    context = {'language': 'en', 'title': (cluster.name + ' guides') if cluster else 'Product guides & stories',
        'description': cluster.description if cluster and cluster.description else 'Explore buying guides, product care and practical shopping advice from Fabrything.',
        'canonical': ORIGIN + path + ('?page=' + str(page) if page > 1 else ''),
        'schema': json.dumps({'@context': 'https://schema.org', '@type': 'CollectionPage', 'name': cluster.name if cluster else 'Fabrything Journal', 'url': ORIGIN + path}),
        'image_url': ORIGIN + '/fabrything-horizontal-light.png', 'topic': cluster, 'topics': public_topics(),
        'articles': batch[:12], 'previous': link(page-1) if page > 1 else None,
        'following': link(page+1) if len(batch) > 12 else None, 'noindex': bool(intent) or not batch}
    response = render(request, 'storefront/journal_document.html', context)
    response['Cache-Control'] = 'public, max-age=0, s-maxage=60'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


def journal_robots(request):
    return HttpResponse('User-agent: *\nAllow: /\nDisallow: /admin/\nDisallow: /account/\nDisallow: /checkout/\nDisallow: /api/\nSitemap: ' + ORIGIN + '/sitemap.xml\n', content_type='text/plain')
