import hashlib
import hmac
import json
import os
import time
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory
from nobleseek.models import Article, PublishingSettings
from .journal import journal_json_ld
from .journal_bridge import JournalBridgeView
from .journal_contract import JournalPayloadSerializer
from .journal_models import JournalArticle, TopicCluster

WORKSPACE = '11111111-1111-4111-8111-111111111111'
PAGE = '22222222-2222-4222-8222-222222222222'
SECRET = 'isolated-test-only-' + 'x' * 32


def payload():
    return {'version': 'fabrything-journal-v1', 'sourceKey': WORKSPACE + ':' + PAGE + ':post-1',
            'workspaceId': WORKSPACE, 'pageId': PAGE, 'title': 'Choose a compatible accessory', 'slug': 'compatible-accessory',
            'excerpt': 'A practical compatibility guide.', 'seoTitle': 'Compatible accessories', 'seoDescription': 'Check compatibility before choosing.',
            'keyword': 'compatible accessories', 'problem': 'Avoid incompatible accessories', 'audience': 'Everyday shoppers',
            'intent': 'buying_guide', 'clusterSlug': 'accessories', 'tags': ['accessories'],
            'sources': [{'title': 'Manufacturer guide', 'url': 'https://example.com/manual'}],
            'products': [{'id': 'one', 'title': 'Accessory', 'platform': 'fabrything', 'url': 'https://www.fabrything.com/product/accessory', 'sourceUrl': 'https://www.fabrything.com/product/accessory', 'specs': {'Compatibility': 'Read the product manual'}}],
            'blocks': [{'type': 'heading', 'text': 'Start with compatibility'}, {'type': 'paragraph', 'text': 'Check the product manual and connector before ordering.'},
                       {'type': 'comparison', 'productIds': ['one'], 'criteria': ['Compatibility']},
                       {'type': 'image', 'alt': 'The connector dimensions to check', 'width': 1200, 'height': 675},
                       {'type': 'faq', 'items': [{'question': 'Where is compatibility listed?', 'answer': 'Read the manufacturer manual.'}]}],
            'editorial': {'reviewed': True}, 'publish': True}


class JournalTests(TestCase):
    def setUp(self):
        self.cluster = TopicCluster.objects.create(name='Accessories', slug='accessories')
        self.env = patch.dict(os.environ, {'ECHOLINK_BLOG_SECRET': SECRET, 'ECHOLINK_BLOG_WORKSPACE_ID': WORKSPACE,
            'ECHOLINK_BLOG_PAGE_ID': PAGE, 'ECHOLINK_BLOG_AUTO_PUBLISH': 'false'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def send(self, data=None, *, stamp=None, secret=SECRET):
        raw = json.dumps(data or payload()).encode()
        stamp = stamp or str(int(time.time()))
        signature = hmac.new(secret.encode(), stamp.encode() + b'.' + raw, hashlib.sha256).hexdigest()
        request = APIRequestFactory().post('/api/store/journal/publish/', data=raw, content_type='application/json',
            HTTP_X_ECHOLINK_TIMESTAMP=stamp, HTTP_X_ECHOLINK_SIGNATURE=signature)
        return JournalBridgeView.as_view()(request)

    def test_signature_expiry_tenant_and_size_fail_closed(self):
        self.assertEqual(self.send(secret='wrong').status_code, 401)
        self.assertEqual(self.send(stamp=str(int(time.time()) - 600)).status_code, 401)
        data = payload(); data['pageId'] = WORKSPACE
        self.assertEqual(self.send(data).status_code, 403)
        self.assertEqual(Article.objects.count(), 0)

    def test_signed_health_check_never_creates_an_article(self):
        stamp = str(int(time.time()))
        signature = hmac.new(SECRET.encode(), stamp.encode() + b'.', hashlib.sha256).hexdigest()
        request = APIRequestFactory().get('/api/store/journal/publish/', HTTP_X_ECHOLINK_TIMESTAMP=stamp, HTTP_X_ECHOLINK_SIGNATURE=signature)
        response = JournalBridgeView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['version'], 'fabrything-journal-v1')
        self.assertEqual(Article.objects.count(), 0)

    def test_receipt_is_idempotent_and_never_overwrites_a_different_article(self):
        first, duplicate = self.send(), self.send()
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.data['status'], 'REVIEW')
        self.assertEqual(duplicate.status_code, 200)
        self.assertTrue(duplicate.data['duplicate'])
        data = payload(); data['title'] = 'Changed title'
        self.assertEqual(self.send(data).status_code, 409)
        self.assertEqual(JournalArticle.objects.count(), 1)
        self.assertEqual(Article.objects.get().headline, payload()['title'])

    def test_signed_receipt_lookup_reconciles_without_writes_or_cross_tenant_access(self):
        self.send()
        stamp = str(int(time.time()))
        signature = hmac.new(SECRET.encode(), stamp.encode() + b'.', hashlib.sha256).hexdigest()

        def lookup(key, supplied_signature=signature):
            request = APIRequestFactory().get('/api/store/journal/publish/', {'sourceKey': key},
                HTTP_X_ECHOLINK_TIMESTAMP=stamp, HTTP_X_ECHOLINK_SIGNATURE=supplied_signature)
            return JournalBridgeView.as_view()(request)

        receipt = lookup(payload()['sourceKey'])
        self.assertEqual(receipt.status_code, 200)
        self.assertEqual(receipt.data['sourceKey'], payload()['sourceKey'])
        self.assertEqual(receipt.data['payloadHash'], JournalArticle.objects.get().payload_hash)
        self.assertNotIn('blocks', receipt.data)
        self.assertEqual(lookup(payload()['sourceKey'], 'wrong').status_code, 401)
        self.assertEqual(lookup(PAGE + ':' + WORKSPACE + ':other').status_code, 403)
        self.assertEqual(lookup(WORKSPACE + ':' + PAGE + ':missing').status_code, 404)
        self.assertEqual(Article.objects.count(), 1)

    def test_destination_policy_and_explicit_review_gate_automatic_publication(self):
        with patch.dict(os.environ, {'ECHOLINK_BLOG_AUTO_PUBLISH': 'true'}):
            policy = PublishingSettings.current(); policy.require_review_for_automation = True; policy.save()
            result = self.send()
        self.assertEqual(result.data['status'], 'PUBLISHED')
        self.assertTrue(PublishingSettings.current().require_review_for_automation)
        self.assertContains(self.client.get('/api/store/journal/document/compatible-accessory/'), 'rel="nofollow noopener sponsored"')
        self.assertContains(self.client.get('/api/store/journal/document/compatible-accessory/'), 'property="og:image"')
        self.assertContains(self.client.get('/api/store/journal/document/compatible-accessory/'), 'Manufacturer guide')
        schema = journal_json_ld(Article.objects.get())
        self.assertIn('Article', [x['@type'] for x in schema['@graph']])
        self.assertIn('FAQPage', [x['@type'] for x in schema['@graph']])
        self.assertNotIn('ratingValue', json.dumps(schema))
        self.assertNotIn('offers', json.dumps(schema))

    def test_unknown_blocks_links_and_missing_images_are_rejected(self):
        for field, value in [('blocks', [{'type': 'script', 'text': '<script>bad()</script>'}]), ('products', [{**payload()['products'][0], 'url': 'javascript:alert(1)'}])]:
            data = payload(); data[field] = value
            self.assertFalse(JournalPayloadSerializer(data=data).is_valid())
        data = payload(); data['blocks'][-2]['src'] = 'https://127.0.0.1/private'
        self.assertFalse(JournalPayloadSerializer(data=data).is_valid())

    def test_future_and_review_articles_do_not_leak_into_public_topics_or_related(self):
        self.send()
        self.assertEqual(self.client.get('/api/store/nobleseek/blog/').status_code, 200)
        self.assertEqual(self.client.get('/api/store/journal/document/compatible-accessory/').status_code, 404)
        self.assertEqual(self.client.get('/api/store/journal/related/compatible-accessory/').json(), [])
        self.assertContains(self.client.get('/api/store/robots.txt'), 'Sitemap: https://www.fabrything.com/sitemap.xml')

    def test_cluster_levels_reject_cycles_and_skipped_depth(self):
        child = TopicCluster(name='Bad child', slug='bad-child', level=3, parent=self.cluster)
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            child.full_clean()

    def test_manual_html_correction_disables_the_older_structured_projection(self):
        self.send()
        from .journal import journal_data
        article = Article.objects.get()
        self.assertIsNotNone(journal_data(article))
        article.body_html += '<p>An editor added a correction.</p>'
        article.save()
        self.assertIsNone(journal_data(article))

    def test_canonical_document_and_topic_archive_share_visible_blocks(self):
        data = payload()
        data['blocks'].insert(1, {'type': 'verdict', 'text': 'Read the manual before buying.'})
        data['blocks'].append({'type': 'pros_cons', 'pros': ['Documented compatibility'], 'cons': ['Check the connector first']})
        with patch.dict(os.environ, {'ECHOLINK_BLOG_AUTO_PUBLISH': 'true'}):
            self.assertEqual(self.send(data).status_code, 201)
        document = self.client.get('/api/store/journal/document/compatible-accessory/')
        for text in ['journal.css', 'Guide contents', 'Quick verdict', 'The trade-offs', 'Common questions', 'nofollow noopener sponsored', 'Read the manual before buying.']:
            self.assertContains(document, text)
        archive = self.client.get('/api/store/journal/archive/accessories/')
        self.assertContains(archive, '/blog/compatible-accessory')
        self.assertContains(archive, 'https://www.fabrything.com/blog/topic/accessories')
        self.assertContains(self.client.get('/api/store/sitemap.xml'), '/blog/topic/accessories')
        self.assertEqual(self.client.get('/api/store/journal/archive/accessories/?page=9999').status_code, 404)
        self.assertEqual(self.client.get('/api/store/journal/archive/missing/').status_code, 404)

    def test_unpublished_clusters_do_not_enter_navigation_or_sitemap(self):
        self.send()
        self.assertEqual(self.client.get('/api/store/journal/topics/').json(), [])
        self.assertNotContains(self.client.get('/api/store/sitemap.xml'), '/blog/topic/accessories')

    def test_malformed_structured_input_returns_validation_errors(self):
        data = payload(); data['blocks'][2]['productIds'] = [{}]
        self.assertFalse(JournalPayloadSerializer(data=data).is_valid())
        data = payload(); data['blocks'][3]['src'] = {'not': 'a URL'}
        self.assertFalse(JournalPayloadSerializer(data=data).is_valid())
