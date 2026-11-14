"""HMAC authenticated, tenant-bound, idempotent EchoLink publishing receiver."""
import hashlib
import hmac
import json
import os
import time
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from nobleseek.models import Article, PublishingSettings
from nobleseek.services_publishing import create_article
from .journal import blocks_html
from .journal_contract import JournalPayloadSerializer
from .journal_models import JournalArticle, TopicCluster


class JournalBridgeView(APIView):
    authentication_classes = []  # This route has its own signed machine authentication.
    permission_classes = [AllowAny]

    def get(self, request):
        secret = os.environ.get('ECHOLINK_BLOG_SECRET', '')
        stamp = request.headers.get('X-EchoLink-Timestamp', '')
        if len(secret) < 32 or not os.environ.get('ECHOLINK_BLOG_PAGE_ID') or not os.environ.get('ECHOLINK_BLOG_WORKSPACE_ID'):
            return Response({'error': 'Journal bridge is not configured.'}, status=503)
        if len(stamp) > 11 or not stamp.isdigit() or abs(time.time() - int(stamp)) > 300:
            return Response({'error': 'Invalid or expired signature.'}, status=401)
        expected = hmac.new(secret.encode(), stamp.encode() + b'.', hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, request.headers.get('X-EchoLink-Signature', '')):
            return Response({'error': 'Invalid or expired signature.'}, status=401)
        source_key = request.query_params.get('sourceKey')
        if source_key:
            prefix = os.environ['ECHOLINK_BLOG_WORKSPACE_ID'] + ':' + os.environ['ECHOLINK_BLOG_PAGE_ID'] + ':'
            if not source_key.startswith(prefix) or len(source_key) > 240:
                return Response({'error': 'Source tenant is not permitted.'}, status=403)
            saved = JournalArticle.objects.select_related('article').filter(source_key=source_key).first()
            if not saved:
                return Response({'error': 'No journal receipt exists for this delivery.'}, status=404)
            return Response({'id': saved.article_id, 'url': saved.article.get_canonical_url(),
                             'status': saved.article.status, 'sourceKey': saved.source_key,
                             'payloadHash': saved.payload_hash})
        return Response({'ok': True, 'version': 'fabrything-journal-v1'})

    def post(self, request):
        secret = os.environ.get('ECHOLINK_BLOG_SECRET', '')
        workspace = os.environ.get('ECHOLINK_BLOG_WORKSPACE_ID', '')
        page = os.environ.get('ECHOLINK_BLOG_PAGE_ID', '')
        if len(secret) < 32 or not workspace or not page:
            return Response({'error': 'Journal bridge is not configured.'}, status=503)
        raw = request.body
        if len(raw) > 200000:
            return Response({'error': 'Article payload is too large.'}, status=413)
        stamp = request.headers.get('X-EchoLink-Timestamp', '')
        if len(stamp) > 11 or not stamp.isdigit() or abs(time.time() - int(stamp)) > 300:
            return Response({'error': 'Invalid or expired signature.'}, status=401)
        expected = hmac.new(secret.encode(), stamp.encode() + b'.' + raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, request.headers.get('X-EchoLink-Signature', '')):
            return Response({'error': 'Invalid or expired signature.'}, status=401)
        serializer = JournalPayloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if str(data['workspaceId']) != workspace or str(data['pageId']) != page or not data['sourceKey'].startswith(workspace + ':' + page + ':'):
            return Response({'error': 'Source tenant is not permitted.'}, status=403)
        digest = hashlib.sha256(raw).hexdigest()
        with transaction.atomic():
            PublishingSettings.locked()
            # Lock the configured silo before checking the receipt to serialize same-topic retries.
            cluster = TopicCluster.objects.select_for_update().filter(slug=data['clusterSlug'], active=True).first()
            if not cluster:
                raise ValidationError({'clusterSlug': 'Configure an active focused topic before accepting articles.'})
            old = JournalArticle.objects.select_related('article').filter(source_key=data['sourceKey']).first()
            if old:
                if old.payload_hash != digest:
                    return Response({'error': 'This delivery key already has different content. Review the saved article; it has not been overwritten.'}, status=409)
                return Response({'id': old.article_id, 'url': old.article.get_canonical_url(), 'status': old.article.status, 'duplicate': True})
            if Article.objects.filter(slug=data['slug']).exists():
                return Response({'error': 'This article slug is already in use.'}, status=409)
            reviewed = data['editorial'].get('reviewed') is True
            permitted = os.environ.get('ECHOLINK_BLOG_AUTO_PUBLISH', '').lower() == 'true'
            status = Article.Status.PUBLISHED if data['publish'] and reviewed and permitted else Article.Status.REVIEW
            article = create_article({'content_type': Article.ContentType.BLOG, 'headline': data['title'],
                'slug': data['slug'], 'excerpt': data['excerpt'], 'body_html': blocks_html(data['blocks'], data['products']),
                'seo_title': data['seoTitle'], 'seo_description': data['seoDescription'], 'tags': data['tags'],
                # Journal automation has its own explicit opt-in above; never
                # disable NobleSeek's independent automated-news review policy.
                'seo_keywords': [data['keyword']], 'status': status}, automation=False)
            image = next((b for b in data['blocks'] if b['type'] == 'image' and b.get('src') and len(b['src']) <= 500), None)
            if image:
                article.hero_image, article.hero_image_alt = image['src'], image['alt']
                article.save(update_fields=['hero_image', 'hero_image_alt', 'updated_at'])
            # Keep native JSON serializable dates after serializer validation.
            products = json.loads(json.dumps(data['products'], default=str))
            JournalArticle.objects.create(article=article, cluster=cluster, intent=data['intent'], problem=data['problem'],
                audience=data['audience'], keyword=data['keyword'], blocks=data['blocks'], products=products,
                sources=data['sources'], editorial={'reviewed': reviewed, 'receivedAt': timezone.now().isoformat()},
                source_key=data['sourceKey'], payload_hash=digest)
            return Response({'id': article.pk, 'url': article.get_canonical_url(), 'status': article.status, 'duplicate': False}, status=201)
