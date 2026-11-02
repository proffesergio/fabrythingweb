from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Users
from catalog.models import ImportSource, Products, ProductVariant, ProductExternalIdentity, SyncJob, SyncRun
from catalog.pricing import quote_supplier_price
from catalog.services_sync_jobs import claim_run, enqueue_due, queue_manual, run_once
from catalog.supplier_security import validate_supplier_url, public_supplier_url
from catalog.google_integrations import provider_configuration, sync_merchant


class SyncPricingTests(TestCase):
    def test_fx_shipping_fee_and_margin_floor(self):
        policy = {'source_currency': 'USD', 'fx_rate_to_bdt': '120',
                  'fx_rate_observed_at': timezone.now().isoformat(),
                  'fee_percent': '2', 'target_margin_percent': '10',
                  'shipping_base_bdt': '40', 'shipping_per_kg_bdt': '20',
                  'weight_grams': 500}
        quote = quote_supplier_price('10', policy)
        self.assertEqual(quote['base_price'], 1200)
        self.assertEqual(quote['shipping_cost'], Decimal('50.00'))
        self.assertIsNone(quote['shipping_fee'])
        self.assertGreaterEqual(quote['selling_price'], 1420.45)
        gross = Decimal(str(quote['selling_price']))
        net_profit = gross * Decimal('0.98') - Decimal('1200') - quote['shipping_cost']
        self.assertGreaterEqual(net_profit, Decimal('100'))

    def test_stale_fx_and_missing_weight_fail_closed(self):
        with self.assertRaisesMessage(ValueError, 'stale'):
            quote_supplier_price('10', {'source_currency': 'USD', 'fx_rate_to_bdt': '120',
                'fx_rate_observed_at': (timezone.now() - timedelta(days=2)).isoformat()})
        with self.assertRaisesMessage(ValueError, 'Weight is required'):
            quote_supplier_price('10', {'shipping_per_kg_bdt': '30'})
        with self.assertRaisesMessage(ValueError, 'timezone'):
            quote_supplier_price('10', {'source_currency': 'USD', 'fx_rate_to_bdt': '120',
                'fx_rate_observed_at': '2026-11-02T12:00:00'})
        with self.assertRaises(ValueError):
            quote_supplier_price('10', {'fee_percent': 'not-a-number'})


class SyncControlTests(TestCase):
    def setUp(self):
        self.staff = Users.objects.create_user(username='sync-admin', email='sync-admin@example.com', password='x', role='Super Admin')
        self.customer = Users.objects.create_user(username='sync-customer', email='sync-customer@example.com', password='x', role='Customer')
        self.source = ImportSource.objects.get(slug='potakait')
        self.client = APIClient()

    def authenticate(self, user):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + str(RefreshToken.for_user(user).access_token))

    def test_customer_and_anonymous_cannot_control_jobs(self):
        url = '/api/products/admin/sync-jobs/'
        self.assertEqual(self.client.post(url, {'mode': 'PRICE', 'source': self.source.id}).status_code, 401)
        self.authenticate(self.customer)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, {'mode': 'PRICE', 'source': self.source.id}).status_code, 403)
        self.assertEqual(SyncJob.objects.count(), 0)

    def test_create_pause_resume_run_and_interval_validation(self):
        self.authenticate(self.staff)
        url = '/api/products/admin/sync-jobs/'
        bad = self.client.post(url, {'mode': 'PRICE', 'source': self.source.id,
            'interval_minutes': 2}, format='json')
        self.assertEqual(bad.status_code, 400)
        response = self.client.post(url, {'mode': 'PRICE', 'source': self.source.id,
            'interval_minutes': 60, 'is_paused': True}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        job_id = response.data['data']['id']
        self.assertEqual(self.client.post(f'{url}{job_id}/resume/').status_code, 200)
        self.assertEqual(self.client.post(f'{url}{job_id}/pause/').status_code, 200)
        self.assertEqual(self.client.post(f'{url}{job_id}/run/').status_code, 202)
        self.assertEqual(self.client.post(f'{url}{job_id}/run/').status_code, 409)
        self.assertEqual(SyncRun.objects.filter(job_id=job_id).count(), 1)

    def test_schedule_and_claim_are_idempotent(self):
        job = SyncJob.objects.create(source=self.source, mode='PRICE', is_paused=False,
            next_run_at=timezone.now() - timedelta(minutes=1), created_by=self.staff)
        self.assertEqual(enqueue_due(), 1)
        self.assertEqual(enqueue_due(), 0)
        run = claim_run()
        self.assertEqual(run.attempt, 1)
        self.assertIsNone(claim_run())
        self.assertEqual(SyncRun.objects.filter(job=job).count(), 1)

    def test_retry_is_bounded_and_audited(self):
        job = SyncJob.objects.create(source=self.source, mode='PRICE', created_by=self.staff)
        run = queue_manual(job, self.staff)
        with patch('catalog.services_sync_jobs.execute_run', side_effect=RuntimeError('no network')):
            run_once()
        run.refresh_from_db()
        self.assertEqual(run.status, SyncRun.STATUS_QUEUED)
        self.assertEqual(run.attempt, 1)
        self.assertEqual(run.error_summary, 'RuntimeError')
        run.available_at = timezone.now() - timedelta(seconds=1)
        run.attempt = 2
        run.save(update_fields=['available_at', 'attempt'])
        with patch('catalog.services_sync_jobs.execute_run', side_effect=RuntimeError('no network')):
            run_once()
        run.refresh_from_db()
        self.assertEqual(run.status, SyncRun.STATUS_FAILED)
        self.assertEqual(run.attempt, 3)

    def test_success_marks_run_and_advances_cursor(self):
        job = SyncJob.objects.create(source=self.source, mode='PRICE', created_by=self.staff)
        run = queue_manual(job, self.staff)
        with patch('catalog.services_sync_jobs.execute_run', return_value={
            'found_count': 1, 'updated_count': 1,
            'result': {'items': [{'product_id': 55, 'updated': True}]}}):
            run_once()
        run.refresh_from_db()
        job.refresh_from_db()
        self.assertEqual(run.status, SyncRun.STATUS_COMPLETED)
        self.assertEqual(job.cursor, 55)
        self.assertIsNotNone(run.finished_at)

    def test_all_failed_batch_retries_then_fails_without_advancing_cursor(self):
        job = SyncJob.objects.create(source=self.source, mode='PRICE', created_by=self.staff)
        run = queue_manual(job, self.staff)
        outcome = {'found_count': 1, 'failed_count': 1, 'updated_count': 0,
                   'result': {'items': [{'product_id': 55, 'updated': False}]}}
        with patch('catalog.services_sync_jobs.execute_run', return_value=outcome):
            run_once()
        run.refresh_from_db()
        job.refresh_from_db()
        self.assertEqual(run.status, SyncRun.STATUS_QUEUED)
        self.assertEqual(job.cursor, 0)
        run.available_at = timezone.now() - timedelta(seconds=1)
        run.attempt = 2
        run.save(update_fields=['available_at', 'attempt'])
        with patch('catalog.services_sync_jobs.execute_run', return_value=outcome):
            run_once()
        run.refresh_from_db()
        self.assertEqual(run.status, SyncRun.STATUS_FAILED)

    def test_partial_batch_is_visible_and_advances_cursor(self):
        job = SyncJob.objects.create(source=self.source, mode='PRICE', created_by=self.staff)
        run = queue_manual(job, self.staff)
        with patch('catalog.services_sync_jobs.execute_run', return_value={
            'found_count': 2, 'updated_count': 1, 'failed_count': 1,
            'result': {'items': [{'product_id': 55}, {'product_id': 56}]}}):
            run_once()
        run.refresh_from_db()
        job.refresh_from_db()
        self.assertEqual(run.status, SyncRun.STATUS_PARTIAL)
        self.assertEqual(job.cursor, 56)

    def test_import_job_browses_next_page(self):
        from catalog.models import Categories
        from catalog.services_sync_jobs import execute_run
        category = Categories.objects.create(name='Test import target', slug='test-import-target', description='')
        job = SyncJob.objects.create(source=self.source, mode='IMPORT', created_by=self.staff,
            target_category=category, category_path='laptops', cursor=2)
        run = SyncRun.objects.create(job=job, scheduled_at=timezone.now(), available_at=timezone.now())
        listing = {'candidates': [{'source_url': 'https://potakait.com/item'}]}
        with patch('catalog.services_sync_jobs.browse_candidates', return_value=listing) as browse, \
             patch('catalog.services_sync_jobs.import_candidates', return_value=[{'status': 'skipped_exists'}]):
            outcome = execute_run(run)
        self.assertEqual(browse.call_args.kwargs['page'], 3)
        self.assertEqual(outcome['result']['page'], 3)

    def test_provider_jobs_are_real_or_explicitly_unconfigured(self):
        self.authenticate(self.staff)
        response = self.client.post('/api/products/admin/sync-jobs/',
            {'mode': 'ANALYTICS', 'interval_minutes': 30}, format='json')
        self.assertEqual(response.status_code, 201)
        insights = self.client.get('/api/products/admin/insights/')
        self.assertEqual(insights.status_code, 200)
        self.assertIn(insights.data['data']['providers']['analytics']['state'],
                      ('unconfigured', 'empty'))
        if insights.data['data']['providers']['analytics']['state'] == 'unconfigured':
            run = self.client.post('/api/products/admin/sync-jobs/' +
                                   str(response.data['data']['id']) + '/run/')
            self.assertEqual(run.status_code, 409)
            self.assertEqual(SyncRun.objects.count(), 0)


class SupplierGuardTests(TestCase):
    def test_host_credentials_and_private_address_rejected(self):
        source = ImportSource.objects.get(slug='potakait')
        with self.assertRaises(ValueError):
            validate_supplier_url('https://evil.example/x', source)
        with self.assertRaises(ValueError):
            validate_supplier_url('https://user:pass@potakait.com/x', source)
        with patch('catalog.supplier_security.socket.getaddrinfo', return_value=[
            (None, None, None, None, ('127.0.0.1', 443))]):
            with self.assertRaisesMessage(ValueError, 'non-public'):
                public_supplier_url('https://potakait.com/x', source)


class GoogleAdapterTests(TestCase):
    def test_unconfigured_is_explicit(self):
        with patch.dict('os.environ', {}, clear=True):
            status = provider_configuration('ANALYTICS')
        self.assertFalse(status['configured'])
        self.assertIn('GA4_PROPERTY_ID', status['missing'])

    def test_merchant_rejects_foreign_currency_without_fx(self):
        with patch.dict('os.environ', {'GOOGLE_MERCHANT_ACCOUNT_ID': '123',
            'GOOGLE_MERCHANT_DATA_SOURCE_ID': '456', 'PUBLIC_STORE_URL': 'https://store.example',
            'STORE_CURRENCY': 'USD'}):
            with self.assertRaisesMessage(ValueError, 'BDT prices'):
                sync_merchant()

    def test_merchant_uses_variant_price_unique_offer_and_persists_identity(self):
        product = Products.objects.create(name='Merchant test item', slug='merchant-test-item',
            description='Test item', sku='NOT-UNIQUE', image=['https://cdn.example/item.jpg'],
            initial_buying_price=100, initial_selling_price=999)
        ProductVariant.objects.create(product=product, sku='VARIANT-1', price=Decimal('149.50'),
                                      stock_quantity=3)
        captured = []
        def send(_session, _url, payload, _params):
            captured.append(payload)
            return {'name': 'accounts/123/productInputs/en~BD~product-1'}
        with patch.dict('os.environ', {'GOOGLE_MERCHANT_ACCOUNT_ID': '123',
             'GOOGLE_MERCHANT_DATA_SOURCE_ID': '456', 'PUBLIC_STORE_URL': 'https://store.example'}), \
             patch('catalog.google_integrations._session', return_value=object()), \
             patch('catalog.google_integrations._post', side_effect=send), \
             patch('catalog.google_integrations.time.sleep'):
            result = sync_merchant()
        self.assertEqual(result['submitted_count'], 1)
        self.assertEqual(captured[0]['offerId'], f'product-{product.id}')
        self.assertEqual(captured[0]['productAttributes']['price']['amountMicros'], '149500000')
        self.assertEqual(ProductExternalIdentity.objects.get(product=product).provider, 'MERCHANT')
