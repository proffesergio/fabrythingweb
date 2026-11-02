"""Database backed sync scheduling and bounded worker execution."""
import uuid
from datetime import timedelta

from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from catalog.google_integrations import fetch_ga4, fetch_search_console, sync_merchant
from catalog.models import SyncJob, SyncRun
from catalog.services_price_sync import sync_source_prices
from catalog.services_scrape_import import browse_candidates, import_candidates

LEASE = timedelta(hours=1)
MAX_ATTEMPTS = 3


def enqueue_due(now=None):
    now = now or timezone.now()
    created = 0
    with transaction.atomic():
        queryset = SyncJob.objects.filter(is_paused=False, next_run_at__lte=now).order_by('id')
        if connection.features.has_select_for_update_skip_locked:
            queryset = queryset.select_for_update(skip_locked=True)
        else:
            queryset = queryset.select_for_update()
        for job in queryset:
            if not job.runs.filter(status__in=[SyncRun.STATUS_QUEUED, SyncRun.STATUS_RUNNING]).exists():
                SyncRun.objects.get_or_create(job=job, scheduled_at=job.next_run_at,
                    defaults={'available_at': now})
                created += 1
            job.next_run_at = now + timedelta(minutes=job.interval_minutes)
            job.save(update_fields=['next_run_at', 'updated_at'])
    return created


def queue_manual(job, user):
    now = timezone.now()
    with transaction.atomic():
        job = SyncJob.objects.select_for_update().get(pk=job.pk)
        if job.runs.filter(status__in=[SyncRun.STATUS_QUEUED, SyncRun.STATUS_RUNNING]).exists():
            raise ValueError('A run is already queued or active for this job.')
        return SyncRun.objects.create(job=job, scheduled_at=now, available_at=now, triggered_by=user)


def claim_run(now=None):
    now = now or timezone.now()
    with transaction.atomic():
        queryset = SyncRun.objects.filter(
            Q(status=SyncRun.STATUS_QUEUED, available_at__lte=now) |
            Q(status=SyncRun.STATUS_RUNNING, lease_until__lte=now)
        ).order_by('available_at', 'id')
        if connection.features.has_select_for_update_skip_locked:
            queryset = queryset.select_for_update(skip_locked=True)
        else:
            queryset = queryset.select_for_update()
        run = queryset.first()
        if run is None:
            return None
        if run.attempt >= MAX_ATTEMPTS:
            run.status = SyncRun.STATUS_FAILED
            run.finished_at = now
            run.lease_until = None
            run.lease_token = None
            run.error_summary = 'Worker lease expired after maximum attempts.'
            run.save(update_fields=['status', 'finished_at', 'lease_until', 'lease_token', 'error_summary'])
            return None
        run.status = SyncRun.STATUS_RUNNING
        run.attempt += 1
        run.lease_token = uuid.uuid4()
        run.lease_until = now + LEASE
        run.started_at = now
        run.save(update_fields=['status', 'attempt', 'lease_token', 'lease_until', 'started_at'])
        return run


def execute_run(run):
    job = run.job
    if job.mode == SyncJob.MODE_IMPORT:
        if job.created_by_id is None:
            raise ValueError('Import job owner account no longer exists.')
        page = min(job.cursor + 1, 1000)
        result = browse_candidates(job.source.slug, category_path=job.category_path,
                                   limit=job.batch_limit, detail=False, page=page)
        if page > 1 and not result['candidates']:
            page = 1
            result = browse_candidates(job.source.slug, category_path=job.category_path,
                                       limit=job.batch_limit, detail=False, page=1)
        urls = [item['source_url'] for item in result['candidates'][:job.batch_limit]]
        owner = job.created_by.domain_user_id or job.created_by
        items = import_candidates(job.source.slug, urls, job.target_category, owner, job.created_by,
                                  pricing_policy=job.pricing_policy)
        return {'found_count': len(urls), 'updated_count': sum(x['status'] == 'imported' for x in items),
                'skipped_count': sum(x['status'] == 'skipped_exists' for x in items),
                'failed_count': sum(x['status'] == 'failed' for x in items),
                'result': {'items': items[:12], 'page': page}}
    if job.mode == SyncJob.MODE_PRICE:
        if not job.source or not job.source.is_enabled or not job.source.sets_source_url:
            raise ValueError('Price source is disabled or no longer a partner source.')
        items = sync_source_prices(source=job.source, limit=job.batch_limit,
                                   pricing_policy=job.pricing_policy, after_id=job.cursor)
        return {'found_count': len(items), 'updated_count': sum(bool(x['updated']) for x in items),
                'failed_count': sum(not x['updated'] for x in items), 'result': {'items': items[:12]}}
    if job.mode == SyncJob.MODE_MERCHANT:
        data = sync_merchant(limit=job.batch_limit, after_id=job.cursor)
        return {'found_count': data['submitted_count'] + data['failed_count'],
                'updated_count': data['submitted_count'], 'failed_count': data['failed_count'], 'result': data}
    if job.mode == SyncJob.MODE_ANALYTICS:
        data = fetch_ga4()
        return {'found_count': data['row_count'], 'result': data}
    if job.mode == SyncJob.MODE_SEARCH_CONSOLE:
        data = fetch_search_console()
        return {'found_count': len(data['queries']), 'result': data}
    raise ValueError('Unsupported sync mode.')


def run_once():
    enqueue_due()
    run = claim_run()
    if run is None:
        return None
    token = run.lease_token
    try:
        outcome = execute_run(run)
    except Exception as exc:
        with transaction.atomic():
            locked = SyncRun.objects.select_for_update().get(pk=run.pk)
            if locked.lease_token != token:
                return locked
            # Network exceptions can include request headers or URLs; keep the
            # audit useful without storing credentials or arbitrary response text.
            locked.error_summary = type(exc).__name__
            if isinstance(exc, ValueError):
                locked.error_summary += ': ' + str(exc)[:200]
            if locked.attempt < MAX_ATTEMPTS:
                locked.status = SyncRun.STATUS_QUEUED
                locked.available_at = timezone.now() + timedelta(minutes=2 ** locked.attempt)
            else:
                locked.status = SyncRun.STATUS_FAILED
                locked.finished_at = timezone.now()
            locked.lease_until = None
            locked.lease_token = None
            locked.save()
        return locked
    with transaction.atomic():
        locked = SyncRun.objects.select_for_update().get(pk=run.pk)
        if locked.lease_token != token:
            return locked
        for key, value in outcome.items():
            setattr(locked, key, value)
        all_failed = locked.found_count > 0 and locked.failed_count == locked.found_count
        if all_failed and locked.attempt < MAX_ATTEMPTS:
            locked.status = SyncRun.STATUS_QUEUED
            locked.available_at = timezone.now() + timedelta(minutes=2 ** locked.attempt)
        else:
            locked.status = (SyncRun.STATUS_FAILED if all_failed else
                SyncRun.STATUS_PARTIAL if locked.failed_count else SyncRun.STATUS_COMPLETED)
            locked.finished_at = timezone.now()
        locked.lease_until = None
        locked.lease_token = None
        locked.error_summary = ('All items failed.' if all_failed else
                                'Some items failed.' if locked.failed_count else '')
        locked.save()
        job = locked.job
        if job.mode == SyncJob.MODE_IMPORT and locked.status in (SyncRun.STATUS_COMPLETED, SyncRun.STATUS_PARTIAL):
            job.cursor = locked.result.get('page', job.cursor)
            job.save(update_fields=['cursor', 'updated_at'])
        if job.mode == SyncJob.MODE_PRICE and locked.status in (
                SyncRun.STATUS_COMPLETED, SyncRun.STATUS_PARTIAL) and locked.result.get('items'):
            job.cursor = locked.result['items'][-1]['product_id']
            job.save(update_fields=['cursor', 'updated_at'])
        if job.mode == SyncJob.MODE_MERCHANT and locked.status in (
                SyncRun.STATUS_COMPLETED, SyncRun.STATUS_PARTIAL):
            job.cursor = locked.result.get('last_product_id', job.cursor)
            job.save(update_fields=['cursor', 'updated_at'])
        if job.source_id and locked.status == SyncRun.STATUS_COMPLETED:
            job.source.last_synced_at = locked.finished_at
            job.source.save(update_fields=['last_synced_at', 'updated_at'])
        return locked
