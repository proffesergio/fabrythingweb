"""Admin product-import tool: browse candidates from reference sites
(potakait.com, canvasit.com.bd, fabrilife.com) and import a picked subset
into our catalog. Sources and their category mappings are DB-driven
(``catalog.models.ImportSource``/``ImportSourceCategory``, managed through
``ImportSourceController``) -- see catalog/services_scrape_import.py for the
browse/import machinery and docs/PRODUCT_IMPORT.md for the owner-facing
how-to.

Both endpoints are platform-staff only (core.helpers.isPlatformStaff), same
rule as every other admin catalog endpoint (AdminSyncPricesView,
AdminProductQuickUpdateView).
"""
from django.db.models import Q
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from catalog.models import Categories, ImportRun, ImportSource
from catalog.services_scrape_import import (
    BROWSE_LIMIT,
    IMPORT_LIMIT,
    DisabledSourceError,
    SourceFetchError,
    UnsupportedSearchError,
    browse_candidates,
    import_candidates,
)
from core.helpers import isPlatformStaff, renderResponse


def _resolve_enabled_source(slug):
    """Look up an ImportSource by slug and check it's usable, returning
    ``(source, error_response)`` -- error_response is None on success. A
    disabled source (e.g. arogga -- no working adapter) is rejected here with
    its own `notes` as the reason, never silently returning empty results."""
    source = ImportSource.objects.filter(slug=slug).first() if slug else None
    if source is None:
        return None, renderResponse(
            data={'source': [f'Unknown source: {slug!r}.']},
            message='Validation error', status=400)
    if not source.is_enabled:
        reason = source.notes or 'this source is currently disabled.'
        return None, renderResponse(
            data={'source': [f'{source.name} is disabled -- {reason}']},
            message='Source is disabled', status=400)
    return source, None


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

        source, error = _resolve_enabled_source(request.query_params.get('source'))
        if error is not None:
            return error

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

        # `detail` drives whether each product page is opened. It is the
        # difference between one request for a whole category and one request
        # PER product, and for a medicine source it is the difference between
        # knowing an item is prescription-only and not. Anything other than an
        # explicit "false" means detailed: guessing wrong towards "fast" would
        # silently report every medicine's Rx status as unknown.
        detail = str(request.query_params.get('detail', 'true')).strip().lower() != 'false'

        try:
            result = browse_candidates(source.slug, category_path=category_path, query=query,
                                       limit=limit, detail=detail)
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
        except (ValueError, DisabledSourceError) as e:
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

    Records one ImportRun per request -- found/imported/skipped/failed
    counts and, if the whole batch blew up before per-item results could be
    produced, an error_summary -- so past syncs are auditable from the admin
    panel instead of only the response of the request that triggered them.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not isPlatformStaff(request.user):
            return renderResponse(data='Forbidden', message='Forbidden', status=403)

        data = request.data
        source, error = _resolve_enabled_source(data.get('source'))
        if error is not None:
            return error

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
        run = ImportRun.objects.create(
            source=source, triggered_by_user_id=request.user, found_count=len(urls))

        try:
            results = import_candidates(source.slug, urls, category, domain_user, request.user)
        except Exception as e:  # noqa: BLE001 -- import_candidates already catches per-item
                                 # failures internally, so reaching here means the whole batch
                                 # blew up (e.g. a category/domain_user problem). That must still
                                 # leave an auditable ImportRun record, not vanish along with a
                                 # bare 500 -- see catalog.services_price_sync's SourceFetchError
                                 # handling in the sibling browse view for the same principle.
            run.mark_finished(status=ImportRun.STATUS_FAILED, error_summary=str(e))
            return renderResponse(data=str(e), message='Import failed', status=500)

        imported = sum(1 for r in results if r['status'] == 'imported')
        skipped = sum(1 for r in results if r['status'] == 'skipped_exists')
        failed = sum(1 for r in results if r['status'] == 'failed')
        run.mark_finished(imported=imported, skipped=skipped, failed=failed)
        source.last_synced_at = timezone.now()
        source.save(update_fields=['last_synced_at', 'updated_at'])

        return renderResponse(
            data={'results': results, 'imported': imported, 'total': len(results), 'run_id': run.id},
            message='Import finished')
