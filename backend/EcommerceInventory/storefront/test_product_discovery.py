"""Public catalog discovery stays bounded, varied, and safe to recommend."""

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Categories, Products
from core.models import StoreConfiguration


class ProductDiscoveryTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.categories = [
            Categories.objects.create(name=f'Category {index}', slug=f'discovery-{index}', description='')
            for index in range(4)
        ]

    def make_product(self, name, category=None, **fields):
        return Products.objects.create(
            name=name, slug=name, sku=name, description='',
            category_id=category, initial_buying_price=10,
            initial_selling_price=20, **fields,
        )

    def test_homepage_discovery_is_bounded_active_distinct_and_varied(self):
        # Older products provide a separate discovery pool; the newest twelve
        # remain in the existing new-arrivals section.
        for index in range(24):
            self.make_product(f'older-{index}', self.categories[index % 4])
        for index in range(12):
            self.make_product(f'new-{index}', self.categories[0])
        self.make_product('inactive', self.categories[1], status='INACTIVE')

        response = self.client.get('/api/store/homepage/')
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()['data']
        arrivals = data['new_arrivals']
        discovered = data['discover_products']

        self.assertEqual(len(arrivals), 12)
        self.assertEqual(len(discovered), 16)
        arrival_ids = {row['id'] for row in arrivals}
        discovered_ids = {row['id'] for row in discovered}
        self.assertEqual(len(discovered_ids), len(discovered))
        self.assertFalse(arrival_ids & discovered_ids)
        self.assertNotIn('inactive', [row['slug'] for row in discovered])
        self.assertEqual({row['category_id'] for row in discovered[:4]},
                         {category.id for category in self.categories})
        self.assertTrue(all('initial_selling_price' in row and 'total_stock' in row
                            for row in discovered))
        self.assertIn('flash_sale', data)
        self.assertIn('best_sellers', data)

    def test_related_products_rank_category_then_brand_then_recent_fallback(self):
        target = self.make_product('target', self.categories[0], brand='Example')
        fallback = self.make_product('fallback', self.categories[2], brand='Other')
        brand = self.make_product('brand', self.categories[1], brand='example')
        category = self.make_product('category', self.categories[0], brand='Other')
        self.make_product('inactive-related', self.categories[0], status='INACTIVE')
        self.make_product('prescription-related', self.categories[0], requires_prescription=True)

        response = self.client.get(f'/api/store/products/{target.slug}/')
        self.assertEqual(response.status_code, 200, response.content)
        rows = response.json()['data']['related_products']
        self.assertEqual([row['slug'] for row in rows], ['category', 'brand', 'fallback'])
        self.assertTrue(all('discount_percentage' in row for row in rows))

    def test_related_falls_back_without_category_and_never_repeats_current(self):
        target = self.make_product('uncategorized', brand='Example')
        self.make_product('same-brand', self.categories[1], brand='Example')
        for index in range(12):
            self.make_product(f'other-{index}', self.categories[2])

        response = self.client.get(f'/api/store/products/{target.slug}/')
        self.assertEqual(response.status_code, 200, response.content)
        slugs = [row['slug'] for row in response.json()['data']['related_products']]
        self.assertEqual(len(slugs), 8)
        self.assertEqual(slugs[0], 'same-brand')
        self.assertEqual(len(slugs), len(set(slugs)))
        self.assertNotIn('uncategorized', slugs)

    def test_homepage_excludes_prescription_products_until_sales_are_enabled(self):
        ordinary = self.make_product('ordinary', self.categories[0])
        rx = self.make_product('prescription', self.categories[1], requires_prescription=True)

        data = self.client.get('/api/store/homepage/').json()['data']
        self.assertIn(ordinary.id, {row['id'] for row in data['new_arrivals']})
        for section in ('new_arrivals', 'discover_products', 'on_sale', 'best_rated',
                        'flash_sale', 'trending', 'best_sellers'):
            self.assertNotIn(rx.id, {row['id'] for row in data[section]}, section)

        config = StoreConfiguration.get_solo()
        config.rx_sales_enabled = True
        config.save()
        data = self.client.get('/api/store/homepage/').json()['data']
        self.assertIn(rx.id, {row['id'] for row in data['new_arrivals']})

    def test_related_respects_prescription_sales_switch(self):
        target = self.make_product('rx-target', self.categories[0], requires_prescription=True)
        rx = self.make_product('rx-related', self.categories[0], requires_prescription=True)
        ordinary = self.make_product('plain-related', self.categories[0])

        rows = self.client.get(f'/api/store/products/{target.slug}/').json()['data']['related_products']
        self.assertEqual([row['id'] for row in rows], [ordinary.id])

        config = StoreConfiguration.get_solo()
        config.rx_sales_enabled = True
        config.save()
        rows = self.client.get(f'/api/store/products/{target.slug}/').json()['data']['related_products']
        self.assertEqual({row['id'] for row in rows}, {rx.id, ordinary.id})
