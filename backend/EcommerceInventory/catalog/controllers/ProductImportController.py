"""Admin product-import tool: browse candidates from reference sites
(potakait.com, canvasit.com.bd, fabrilife.com) and import a picked subset
into our catalog. See catalog/services_scrape_import.py for the machinery
and docs/PRODUCT_IMPORT.md for the owner-facing how-to.

Both endpoints are platform-staff only (core.helpers.isPlatformStaff), same
rule as every other admin catalog endpoint (AdminSyncPricesView,
AdminProductQuickUpdateView).
"""
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from catalog.models import Categories
from catalog.services_scrape_import import (
    BROWSE_LIMIT,
    IMPORT_LIMIT,
    SOURCES,
    SourceFetchError,
    UnsupportedSearchError,
    browse_candidates,
    import_candidates,
)
from core.helpers import isPlatformStaff, renderResponse


class AdminBrowseImportCandidatesView(APIView):
    """GET /api/products/admin/import/browse/?source=potakait&category=smart-phone
    GET /api/products/admin/import/browse/?source=fabrilife&q=hoodie

    Returns {candidates: [...], categories: [...]} -- see
    catalog.services_scrape_import.browse_candidates.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not isPlatformStaff(request.user):
            return renderResponse(data='Forbidden', message='Forbidden', status=403)

        source = request.query_params.get('source')
        if source not in SOURCES:
            return renderResponse(
                data={'source': [f'Must be one of {sorted(SOURCES)}.']},
                message='Validation error', status=400)

        category_path = request.query_params.get('category') or None
        query = request.query_params.get('q') or None
        if not category_path and not query:
            return renderResponse(
                data={'category': ['Provide a category or a search term.']},
                message='Validation error', status=400)

        try:
            limit = int(request.query_params.get('limit', BROWSE_LIMIT))
        except (TypeError, ValueError):
            limit = BROWSE_LIMIT

        try:
            result = browse_candidates(source, category_path=category_path, query=query, limit=limit)
        except SourceFetchError as e:
            return renderResponse(data=str(e), message='Could not fetch that listing', status=502)
        except UnsupportedSearchError as e:
            # Distinct from the generic "provide a category or search term"
            # ValueError below: this is specifically about `q`, so it's
            # attributed to that field rather than `category` -- the UI
            # should already be hiding the search box for a source without
            # search support, but the API refuses it either way rather than
            # ever returning an empty "no results" list that looks like a
            # genuine zero-result search.
            return renderResponse(data={'q': [str(e)]}, message='Validation error', status=400)
        except ValueError as e:
            return renderResponse(data={'category': [str(e)]}, message='Validation error', status=400)

        return renderResponse(data=result, message='Candidates fetched')


class AdminImportProductsView(APIView):
    """POST /api/products/admin/import/
    body: {source, source_urls: [...], category_id (or category slug)}

    Capped at IMPORT_LIMIT products per request (see
    catalog.services_scrape_import for why -- 1 req/sec partner-site
    etiquette makes a bigger batch too slow for one request). Never silently
    truncates: an over-cap request is rejected with a clear message so the
    admin can split it into multiple runs.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not isPlatformStaff(request.user):
            return renderResponse(data='Forbidden', message='Forbidden', status=403)

        data = request.data
        source = data.get('source')
        if source not in SOURCES:
            return renderResponse(
                data={'source': [f'Must be one of {sorted(SOURCES)}.']},
                message='Validation error', status=400)

        urls = data.get('source_urls') or []
        if not isinstance(urls, list) or not urls:
            return renderResponse(
                data={'source_urls': ['Select at least one product to import.']},
                message='Validation error', status=400)
        if len(urls) > IMPORT_LIMIT:
            return renderResponse(
                data={'source_urls': [
                    f'Import is capped at {IMPORT_LIMIT} products per request '
                    f'(reference sites are rate-limited to 1 request/second) -- '
                    f'select fewer and run again.']},
                message='Validation error', status=400)

        category_ref = data.get('category_id') or data.get('category')
        if not category_ref:
            return renderResponse(
                data={'category_id': ['Target category is required.']},
                message='Validation error', status=400)
        lookup = Q(id=category_ref) if str(category_ref).isdigit() else Q(slug=category_ref)
        category = Categories.objects.filter(lookup).first()
        if category is None:
            return renderResponse(
                data={'category_id': ['Category not found.']},
                message='Validation error', status=400)

        domain_user = request.user.domain_user_id or request.user
        results = import_candidates(source, urls, category, domain_user, request.user)
        imported = sum(1 for r in results if r['status'] == 'imported')
        return renderResponse(
            data={'results': results, 'imported': imported, 'total': len(results)},
            message='Import finished')
