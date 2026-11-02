"""The public sitemap lists only URLs visitors can open."""

from datetime import timedelta
from xml.etree import ElementTree

from django.test import TestCase
from django.utils import timezone

from catalog.models import Products
from nobleseek.models import Article


SITEMAP = '/api/store/sitemap.xml'
NS = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}


class SitemapTests(TestCase):
    def locations(self):
        response = self.client.get(SITEMAP)
        self.assertEqual(response.status_code, 200)
        root = ElementTree.fromstring(response.content)
        self.assertEqual(root.tag, f"{{{NS['s']}}}urlset")
        return response, {node.text for node in root.findall('s:url/s:loc', NS)}

    def test_lists_canonical_static_and_active_product_urls(self):
        Products.objects.create(
            name='Visible', slug='visible-product', description='d', sku='SEO-1',
            initial_buying_price=10, initial_selling_price=20, status='ACTIVE',
        )
        Products.objects.create(
            name='Hidden', slug='hidden-product', description='d', sku='SEO-2',
            initial_buying_price=10, initial_selling_price=20, status='INACTIVE',
        )

        response, locations = self.locations()

        self.assertIn('https://www.fabrything.com/', locations)
        self.assertIn('https://www.fabrything.com/shop', locations)
        self.assertIn('https://www.fabrything.com/product/visible-product', locations)
        self.assertNotIn('https://www.fabrything.com/product/hidden-product', locations)
        self.assertTrue(all(url.startswith('https://www.fabrything.com/') for url in locations))
        self.assertEqual(response['Content-Type'], 'application/xml')
        self.assertEqual(
            response['Cache-Control'],
            'public, max-age=0, s-maxage=300, stale-while-revalidate=60',
        )

    def test_lists_published_articles_but_not_drafts_or_scheduled_articles(self):
        Article.objects.create(
            headline='Visible story', slug='visible-story', body_html='<p>Visible</p>',
            status=Article.Status.PUBLISHED,
        )
        Article.objects.create(
            headline='Draft story', slug='draft-story', body_html='<p>Draft</p>',
            status=Article.Status.DRAFT,
        )
        Article.objects.create(
            headline='Future story', slug='future-story', body_html='<p>Future</p>',
            status=Article.Status.PUBLISHED,
            published_at=timezone.now() + timedelta(days=1),
        )

        _, locations = self.locations()

        self.assertIn('https://www.fabrything.com/nobleseek/visible-story', locations)
        self.assertNotIn('https://www.fabrything.com/nobleseek/draft-story', locations)
        self.assertNotIn('https://www.fabrything.com/nobleseek/future-story', locations)
