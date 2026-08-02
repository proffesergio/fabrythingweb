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

from catalog.models import ImportSourceCategory
from catalog.services_import import import_image
from catalog.services_scrape_import import (
    LISTING_ONLY_LIMIT,
    DisabledSourceError,
    SourceFetchError,
    UnsupportedSearchError,
    browse_candidates,
)
from core.helpers import renderResponse

from .models import AffiliateProduct
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
            return renderResponse(data=str(e), message='Could not fetch that listing', status=502)
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


class AdminAffiliateListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPlatformStaff]

    def get(self, request):
        qs = AffiliateProduct.objects.all().prefetch_related('grid_categories')
        data = AffiliateProductAdminSerializer(qs, many=True, context={'request': request}).data
        return renderResponse(data=data, message='Affiliate products retrieved')

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
