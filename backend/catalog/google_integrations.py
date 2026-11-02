"""Environment configured Google API adapters. No credentials enter the database."""
import os
import re
import time
from datetime import timedelta
from decimal import Decimal
from urllib.parse import quote

from django.utils import timezone

from catalog.models import Products, ProductExternalIdentity


SCOPES = {
    'MERCHANT': 'https://www.googleapis.com/auth/content',
    'ANALYTICS': 'https://www.googleapis.com/auth/analytics.readonly',
    'SEARCH_CONSOLE': 'https://www.googleapis.com/auth/webmasters.readonly',
}


class ProviderNotConfigured(ValueError):
    pass


def provider_configuration(mode):
    required = {
        'MERCHANT': ['GOOGLE_MERCHANT_ACCOUNT_ID', 'GOOGLE_MERCHANT_DATA_SOURCE_ID', 'PUBLIC_STORE_URL'],
        'ANALYTICS': ['GA4_PROPERTY_ID'],
        'SEARCH_CONSOLE': ['SEARCH_CONSOLE_SITE_URL'],
    }[mode]
    missing = [key for key in required if not os.environ.get(key)]
    if not (os.environ.get('GOOGLE_APPLICATION_CREDENTIALS') or os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')):
        missing.append('GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_SERVICE_ACCOUNT_JSON')
    return {'configured': not missing, 'missing': missing}


def _session(mode):
    status = provider_configuration(mode)
    if not status['configured']:
        raise ProviderNotConfigured('Missing configuration: ' + ', '.join(status['missing']))
    from google.auth.transport.requests import AuthorizedSession
    from google.oauth2 import service_account
    path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if path:
        credentials = service_account.Credentials.from_service_account_file(path, scopes=[SCOPES[mode]])
    else:
        import json
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_JSON']), scopes=[SCOPES[mode]])
    return AuthorizedSession(credentials)


def _post(session, url, payload, params=None):
    response = session.post(url, json=payload, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def sync_merchant(limit=12, after_id=0):
    account = os.environ['GOOGLE_MERCHANT_ACCOUNT_ID']
    source = os.environ['GOOGLE_MERCHANT_DATA_SOURCE_ID']
    if not account.isdigit() or not source.isdigit():
        raise ValueError('Merchant account and data source IDs must be numeric.')
    store = os.environ['PUBLIC_STORE_URL'].rstrip('/')
    if not store.startswith('https://'):
        raise ValueError('PUBLIC_STORE_URL must be HTTPS.')
    currency = os.environ.get('STORE_CURRENCY', 'BDT')
    if currency != 'BDT':
        raise ValueError('Merchant export requires BDT prices; conversion needs a verified FX rate.')
    session = _session('MERCHANT')
    endpoint = f'https://merchantapi.googleapis.com/products/v1/accounts/{account}/productInputs:insert'
    items_query = Products.objects.filter(status='ACTIVE').order_by('id')
    if after_id:
        later = items_query.filter(id__gt=after_id)
        items_query = later if later.exists() else items_query
    items = list(items_query[:limit])
    accepted = 0
    failures = []
    for item in items:
        try:
            time.sleep(0.2)
            variants = list(item.variants.filter(is_active=True))
            if not variants:
                raise ValueError('Product has no active sellable variants')
            variant_prices = {v.effective_price for v in variants}
            if len(variant_prices) != 1:
                raise ValueError('Product variants have different prices; parent offer would be inaccurate')
            amount = Decimal(str(variant_prices.pop()))
            if not amount.is_finite() or amount <= 0:
                raise ValueError('Invalid selling price')
            image = item.image[0] if isinstance(item.image, list) and item.image else None
            if not image or not str(image).startswith('https://'):
                raise ValueError('Product needs a public HTTPS image')
            payload = {
                'offerId': f'product-{item.id}', 'contentLanguage': 'en', 'feedLabel': 'BD',
                'productAttributes': {
                    'title': item.name, 'description': item.description[:5000],
                    'link': f'{store}/product/{quote(item.slug)}/', 'imageLink': image,
                    'availability': 'IN_STOCK' if item.total_stock > 0 else 'OUT_OF_STOCK',
                    'condition': 'NEW', 'price': {
                        'amountMicros': str(int(amount * Decimal('1000000'))),
                        'currencyCode': currency},
                },
            }
            if item.brand:
                payload['productAttributes']['brand'] = item.brand
            if item.brand_model:
                payload['productAttributes']['mpn'] = item.brand_model
            submitted = _post(session, endpoint, payload,
                              {'dataSource': f'accounts/{account}/dataSources/{source}'})
            external_name = submitted.get('name')
            if not external_name or not external_name.startswith(f'accounts/{account}/productInputs/'):
                raise ValueError('Merchant response lacked a product input identifier.')
            ProductExternalIdentity.objects.update_or_create(product=item, provider='MERCHANT',
                defaults={'external_name': external_name})
            accepted += 1
        except Exception as exc:  # per-product failure remains visible and bounded
            failures.append({'product_id': item.id, 'error': type(exc).__name__})
    return {'submitted_count': accepted, 'failed_count': len(failures), 'failures': failures,
            'last_product_id': items[-1].id if items else 0,
            'note': 'Submitted inputs; Google processing and approval are separate.'}


def fetch_ga4(days=30):
    prop = os.environ['GA4_PROPERTY_ID']
    if not prop.isdigit():
        raise ValueError('GA4_PROPERTY_ID must be numeric.')
    session = _session('ANALYTICS')
    response = _post(session, f'https://analyticsdata.googleapis.com/v1beta/properties/{prop}:runReport', {
        'dateRanges': [{'startDate': f'{days}daysAgo', 'endDate': 'yesterday'}],
        'dimensions': [{'name': 'eventName'}], 'metrics': [{'name': 'eventCount'}], 'limit': 100,
    })
    events = {row['dimensionValues'][0]['value']: int(row['metricValues'][0]['value'])
              for row in response.get('rows', [])}
    item_response = _post(session, f'https://analyticsdata.googleapis.com/v1beta/properties/{prop}:runReport', {
        'dateRanges': [{'startDate': f'{days}daysAgo', 'endDate': 'yesterday'}],
        'dimensions': [{'name': 'itemId'}, {'name': 'itemName'}],
        'metrics': [{'name': 'itemsViewed'}, {'name': 'itemsAddedToCart'},
                    {'name': 'itemsCheckedOut'}, {'name': 'itemsPurchased'}],
        'limit': 100,
    })
    product_funnels = [{
        'item_id': row['dimensionValues'][0]['value'],
        'item_name': row['dimensionValues'][1]['value'],
        'views': int(row['metricValues'][0]['value']),
        'adds_to_cart': int(row['metricValues'][1]['value']),
        'checkouts': int(row['metricValues'][2]['value']),
        'purchases': int(row['metricValues'][3]['value']),
    } for row in item_response.get('rows', [])]
    return {'events': events, 'funnel': [
        {'stage': name, 'count': events.get(name, 0)}
        for name in ('view_item', 'add_to_cart', 'begin_checkout', 'purchase')],
        'row_count': int(response.get('rowCount', 0)), 'product_funnels': product_funnels}


def fetch_search_console(days=30):
    site = os.environ['SEARCH_CONSOLE_SITE_URL']
    if not (site.startswith('https://') or site.startswith('sc-domain:')):
        raise ValueError('SEARCH_CONSOLE_SITE_URL must be an HTTPS URL or domain property.')
    session = _session('SEARCH_CONSOLE')
    today = timezone.now().date()
    response = _post(session,
        f'https://www.googleapis.com/webmasters/v3/sites/{quote(site, safe="")}/searchAnalytics/query',
        {'startDate': (today - timedelta(days=days + 1)).isoformat(),
         'endDate': (today - timedelta(days=2)).isoformat(),
         'dimensions': ['query'], 'rowLimit': 250})
    return {'queries': [{'query': row['keys'][0], 'clicks': row['clicks'],
                         'impressions': row['impressions'], 'ctr': row['ctr']}
                        for row in response.get('rows', [])]}
