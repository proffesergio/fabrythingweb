"""Rokomari affiliate automation endpoints.

Admin (`/api/store/admin/affiliate/...`, IsPlatformStaff): search Rokomari for
candidates (reuses catalog.services_scrape_import.browse_candidates -- the
same rokomari adapter + ImportSource machinery the regular catalog import
tool already uses, not a second scraper), bulk-add selected candidates as
AffiliateProducts with links constructed lazily and images re-hosted, CRUD,
reorder.

Public (`/api/store/affiliate/...`, no auth): list active affiliate products
filtered by placement, and the click-through redirect that is the only
sanctioned way a customer ever reaches the affiliate site -- see
AffiliateClickRedirectView for why.
"""
from django.db import transaction
from django.db.models import F
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from catalog.models import ImportSource, ImportSourceCategory
from catalog.scrape_parsers import parse_rokomari_listing_cards
from catalog.services_import import import_image
from catalog.services_scrape_import import (
    LISTING_ONLY_LIMIT,
    DisabledSourceError,
    SourceFetchError,
    UnsupportedSearchError,
    browse_candidates,
)
from core.helpers import renderResponse

from .models import AffiliateConfig, AffiliateProduct
from .permissions import IsPlatformStaff
from .serializers_affiliate import AffiliateProductAdminSerializer, AffiliateProductPublicSerializer
from .services_affiliate import UnsupportedProgramError, build_affiliate_link, extract_rokomari_product_id

ROKOMARI_SOURCE_SLUG = "rokomari"

# Fallback default category (Rokomari's Beauty & Health top-level page) for
# when the admin opens the picker with no q/category AND, somehow, no
# ImportSourceCategory rows are seeded for rokomari -- shouldn't happen in
# practice (the 0012 migration seeds 15 of them) but this keeps "browse with
# nothing typed yet" from ever 400ing.
DEFAULT_ROKOMARI_CATEGORY_PATH = "product/category/2355/beauty-health"

# Bulk-add is capped the same way the catalog import tool caps IMPORT_LIMIT:
# each candidate's image download is one more request against Rokomari, and
# polite_get enforces 1 req/sec, so an unbounded batch would blow past a
# typical gateway timeout and hammer the site besides.
AFFILIATE_BULK_ADD_LIMIT = 12


class AdminAffiliateSearchView(APIView):
    """GET /api/store/admin/affiliate/search/?q=perfume
    GET /api/store/admin/affiliate/search/?category=product/category/2618/perfume
    GET /api/store/admin/affiliate/search/  (no params -- see below)

    Thin wrapper over the existing browse_candidates() used by the regular
    catalog product-import tool, pinned to the rokomari source, with each
    candidate's Rokomari productId extracted so the bulk-add step never has
    to re-derive it.

    Always calls browse_candidates(detail=False): the picker only needs
    name/brand/price/image, which rokomari's listing card already carries,
    so there's no need to fetch each product page individually -- see
    catalog.services_scrape_import.browse_candidates's docstring for why that
    per-product loop was a live 502.

    No q/category -> defaults to the first configured rokomari
    ImportSourceCategory (Beauty & Health is the owner's stated area of
    interest, and that's what's seeded) instead of 400ing, so the admin can
    open the picker and immediately see products without typing anything.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPlatformStaff]

    def get(self, request):
        category_path = request.query_params.get('category') or None
        query = request.query_params.get('q') or None
        if not category_path and not query:
            default_cat = ImportSourceCategory.objects.filter(
                source__slug=ROKOMARI_SOURCE_SLUG).order_by('display_order', 'id').first()
            category_path = default_cat.source_path if default_cat else DEFAULT_ROKOMARI_CATEGORY_PATH

        try:
            limit = int(request.query_params.get('limit', LISTING_ONLY_LIMIT))
        except (TypeError, ValueError):
            limit = LISTING_ONLY_LIMIT

        try:
            result = browse_candidates(
                ROKOMARI_SOURCE_SLUG, category_path=category_path, query=query, limit=limit, detail=False)
        except SourceFetchError as e:
            # str(e) on a requests HTTPError is e.g. "403 Client Error:
            # Forbidden for url: ..." -- the reason belongs in `message` so it
            # is visible in the admin panel without expanding a console array.
            return renderResponse(data=str(e), message=f'Could not fetch that listing: {e}', status=502)
        except UnsupportedSearchError as e:
            return renderResponse(data={'q': [str(e)]}, message='Validation error', status=400)
        except (ValueError, DisabledSourceError) as e:
            return renderResponse(data={'category': [str(e)]}, message='Validation error', status=400)

        candidates = [
            {**c, 'remote_product_id': extract_rokomari_product_id(c['source_url'])}
            for c in result['candidates']
        ]
        return renderResponse(data={**result, 'candidates': candidates}, message='Candidates fetched')


class AdminAffiliateBulkAddView(APIView):
    """POST /api/store/admin/affiliate/bulk-add/
    body: {"candidates": [{"source_url", "name", "brand", "price",
    "discount_price", "images": [...], "link_type"}, ...]}

    Capped at AFFILIATE_BULK_ADD_LIMIT per request. A candidate missing a
    derivable Rokomari productId, or already added, is skipped (reported, not
    silently dropped) rather than aborting the whole batch.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPlatformStaff]

    def post(self, request):
        items = request.data.get('candidates')
        if not isinstance(items, list) or not items:
            return renderResponse(
                data={'candidates': ['Select at least one product to add.']},
                message='Validation error', status=400)
        if len(items) > AFFILIATE_BULK_ADD_LIMIT:
            return renderResponse(
                data={'candidates': [
                    f'Bulk-add is capped at {AFFILIATE_BULK_ADD_LIMIT} products per request '
                    f'(Rokomari is rate-limited to 1 request/second) -- select fewer and run again.']},
                message='Validation error', status=400)

        created_ids = []
        skipped = []
        for item in items:
            source_url = (item or {}).get('source_url')
            remote_id = (item or {}).get('remote_product_id') or extract_rokomari_product_id(source_url or '')
            if not source_url or not remote_id:
                skipped.append({'source_url': source_url, 'reason': 'could not determine the Rokomari product id'})
                continue
            if AffiliateProduct.objects.filter(program=ROKOMARI_SOURCE_SLUG, remote_product_id=str(remote_id)).exists():
                skipped.append({'source_url': source_url, 'reason': 'already added'})
                continue

            image_url = ''
            images = item.get('images') or []
            if images:
                image_url = import_image(images[0]) or ''

            product = AffiliateProduct.objects.create(
                program=ROKOMARI_SOURCE_SLUG,
                remote_product_id=str(remote_id),
                source_url=source_url,
                title=item.get('name') or item.get('title') or '',
                brand=item.get('brand') or '',
                image=image_url,
                original_price=item.get('price') or None,
                current_price=item.get('discount_price') or item.get('price') or None,
                commission_amount=item.get('commission_amount') or None,
                link_type=item.get('link_type') or 'CART',
            )
            created_ids.append(product.id)

        return renderResponse(
            data={'created': created_ids, 'skipped': skipped, 'total': len(items)},
            message='Bulk add finished')


def _rokomari_categories():
    """The seeded rokomari ImportSourceCategory rows, for the picker's
    dropdown. Returned by the list endpoint rather than only by a successful
    browse: an admin needs to be able to CHOOSE a category precisely when
    browsing is failing, and a free-text path field invites typing our own
    taxonomy slug (`beauty-health`) instead of the source path
    (`product/category/2355/beauty-health`), which fetches a 404."""
    try:
        source = ImportSource.objects.filter(slug=ROKOMARI_SOURCE_SLUG).first()
        if not source:
            return []
        return [
            {'path': c.source_path, 'label': c.label or c.source_path}
            for c in source.categories.all()
        ]
    except Exception:  # noqa: BLE001 -- a picker convenience must never 500 the list
        return []


class AdminAffiliateListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPlatformStaff]

    def get(self, request):
        qs = AffiliateProduct.objects.all().prefetch_related('grid_categories')
        data = AffiliateProductAdminSerializer(qs, many=True, context={'request': request}).data
        return renderResponse(
            data={'products': data, 'categories': _rokomari_categories()},
            message='Affiliate products retrieved')

    def post(self, request):
        serializer = AffiliateProductAdminSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message='Validation error', status=400)
        serializer.save()
        return renderResponse(data=serializer.data, message='Affiliate product created', status=201)


class AdminAffiliateDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPlatformStaff]

    def get_object(self, pk):
        return get_object_or_404(AffiliateProduct, pk=pk)

    def get(self, request, pk):
        obj = self.get_object(pk)
        return renderResponse(
            data=AffiliateProductAdminSerializer(obj, context={'request': request}).data,
            message='Affiliate product retrieved')

    def patch(self, request, pk):
        obj = self.get_object(pk)
        serializer = AffiliateProductAdminSerializer(obj, data=request.data, partial=True, context={'request': request})
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message='Validation error', status=400)
        serializer.save()
        return renderResponse(data=serializer.data, message='Affiliate product updated')

    def put(self, request, pk):
        return self.patch(request, pk)

    def delete(self, request, pk):
        obj = self.get_object(pk)
        obj.delete()
        return renderResponse(data=None, message='Affiliate product deleted')


class AdminAffiliateReorderView(APIView):
    """POST {"order": [id, id, ...]} in the desired display order -- same
    shape/behaviour as storefront.views_banners.AdminBannerReorderView."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPlatformStaff]

    def post(self, request):
        order = request.data.get('order')
        if not isinstance(order, list) or not order:
            return renderResponse(
                data='`order` must be a non-empty list of affiliate product ids',
                message='Validation error', status=400)

        with transaction.atomic():
            for index, pid in enumerate(order):
                AffiliateProduct.objects.filter(pk=pid).update(display_order=index)

        qs = AffiliateProduct.objects.all().prefetch_related('grid_categories')
        return renderResponse(
            data=AffiliateProductAdminSerializer(qs, many=True, context={'request': request}).data,
            message='Affiliate products reordered')


class PublicAffiliateListView(APIView):
    """GET /api/store/affiliate/?placement=sidebar
    GET /api/store/affiliate/?placement=deals
    GET /api/store/affiliate/?category=<taxonomy-slug>

    No query params -> every active, in-window product (any placement).
    """
    permission_classes = [AllowAny]

    def get(self, request):
        category = request.query_params.get('category')
        placement = request.query_params.get('placement')

        qs = AffiliateProduct.objects.prefetch_related('grid_categories')
        if category:
            qs = qs.for_category(category)
        elif placement == 'sidebar':
            qs = qs.for_sidebar()
        elif placement == 'deals':
            qs = qs.for_deals_page()
        else:
            qs = qs.active()

        data = AffiliateProductPublicSerializer(qs, many=True, context={'request': request}).data
        return renderResponse(data=data, message='Affiliate products retrieved')


class AffiliateClickRedirectView(APIView):
    """GET /api/store/affiliate/<pk>/go/ -- the ONLY sanctioned path from our
    site to the affiliate target. Public (no auth): this is a link a customer
    clicks, not an API call a logged-in client makes.

    Increments click_count atomically (F() expression, never read-modify-
    write -- this counter is how the owner spots attribution breaking, by
    comparing it against Rokomari's own dashboard count, so it must never
    lose an increment to a race) then 302s to the resolved target.

    404s for a product that is inactive, deleted, or outside its scheduling
    window -- get_object_or_404 against the same `.active()` queryset every
    other public surface uses, so "not currently promoted" and "doesn't
    exist" look identical from the outside, which is the correct behaviour
    for a promo link that expired.
    """
    permission_classes = [AllowAny]

    def get(self, request, pk):
        product = get_object_or_404(AffiliateProduct.objects.active(), pk=pk)
        AffiliateProduct.objects.filter(pk=product.pk).update(click_count=F('click_count') + 1)
        try:
            target = build_affiliate_link(product)
        except UnsupportedProgramError:
            # No adapter and no manual override -- there is genuinely nowhere
            # to send the customer. Treat it the same as "not promoted"
            # rather than a 500, since from the customer's side both mean
            # "this link doesn't work right now".
            from django.http import Http404
            raise Http404
        return HttpResponseRedirect(target)


class AdminAffiliateParseUrlView(APIView):
    """POST /api/store/admin/affiliate/parse-url/  body: {"url": "..."}

    Pure parsing, NO network fetch -- which is the whole point. rokomari.com
    sits behind Cloudflare bot protection that answers this server's IP with a
    403 "Just a moment..." interstitial, so the browse/import path cannot work
    from here. Building the affiliate link, though, only needs the numeric
    productId out of the URL, and that is pure string work.

    So the owner pastes a product URL from his own browser (where the site
    loads fine), we hand back the productId and a preview of the outbound link,
    and he fills in title/price/image. Slower than scraping, but it works today
    and does not fight anyone's bot protection.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPlatformStaff]

    def post(self, request):
        url = (request.data.get('url') or '').strip()
        if not url:
            return renderResponse(
                data={'url': ['Paste a Rokomari product URL.']},
                message='Validation error', status=400)

        remote_id = extract_rokomari_product_id(url)
        if not remote_id:
            return renderResponse(
                data={'url': [
                    "That doesn't look like a Rokomari product page. It should "
                    "look like https://www.rokomari.com/product/531074/..."
                ]},
                message='Validation error', status=400)

        cfg = AffiliateConfig.get_solo()
        preview = {
            'cart': _preview_link(cfg, remote_id, 'CART'),
            'product': _preview_link(cfg, remote_id, 'PRODUCT'),
        }
        return renderResponse(
            data={'remote_product_id': remote_id, 'source_url': url, 'links': preview},
            message='URL parsed')


def _preview_link(cfg, remote_id, link_type):
    """Build the outbound URL without needing a saved AffiliateProduct row --
    the admin wants to see the link before committing the record."""
    stub = AffiliateProduct(
        program='rokomari', remote_product_id=remote_id,
        source_url='', link_type=link_type, manual_short_link='',
    )
    try:
        return build_affiliate_link(stub)
    except UnsupportedProgramError as e:
        return str(e)


class AdminAffiliateDiagnosticView(APIView):
    """GET /api/store/admin/affiliate/diagnose/?path=product/category/2355/beauty-health

    One raw fetch, reporting exactly what the SERVER sees. Every rokomari
    browse has been failing in production with a 502 while the identical URL
    returns 200 with 60 product cards from a developer machine -- the classic
    signature of the host blocking datacenter IPs. Guessing at that from the
    outside wastes deploy cycles; this answers it in one request.

    Returns the upstream status, elapsed time, response size and the first
    bytes of the body (enough to recognise a Cloudflare challenge or a block
    page) instead of collapsing everything into "could not fetch".
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPlatformStaff]

    def get(self, request):
        import time as _time

        import requests

        from tools.scrape.common import UA

        source = ImportSource.objects.filter(slug=ROKOMARI_SOURCE_SLUG).first()
        base = (source.base_url if source else 'https://www.rokomari.com/')
        # `url=` tests an arbitrary address (e.g. the image CDN on a different
        # host, which may not sit behind the same bot protection as the site);
        # `path=` stays relative to the source's own base.
        explicit = request.query_params.get('url')
        if explicit:
            url = explicit
        else:
            path = request.query_params.get('path') or 'product/category/2355/beauty-health'
            url = base + path.lstrip('/')

        started = _time.monotonic()
        try:
            r = requests.get(url, headers=UA, timeout=20)
            body = r.text or ''
            return renderResponse(data={
                'url': url,
                'status': r.status_code,
                'elapsed_ms': int((_time.monotonic() - started) * 1000),
                'bytes': len(body),
                'server': r.headers.get('server'),
                'content_type': r.headers.get('content-type'),
                'body_head': body[:400],
                # The parser is the real test: a 200 that yields zero cards
                # means we were served something other than the listing.
                'cards_parsed': len(parse_rokomari_listing_cards(body, base)) if r.status_code == 200 else 0,
            }, message='Diagnostic complete')
        except Exception as e:  # noqa: BLE001 -- reporting the failure IS the point
            return renderResponse(data={
                'url': url,
                'error_type': type(e).__name__,
                'error': str(e),
                'elapsed_ms': int((_time.monotonic() - started) * 1000),
            }, message='Fetch raised', status=200)
