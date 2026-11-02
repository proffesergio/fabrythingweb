"""Staff-only controls and operational insight for catalog syncs."""
from datetime import timedelta
import re

from django.db import transaction
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from catalog.google_integrations import provider_configuration
from catalog.models import ProductVariant, SyncJob, SyncRun
from catalog.services_sync_jobs import queue_manual
from catalog.pricing import quote_supplier_price
from core.helpers import isPlatformStaff, renderResponse
from orders.models import Order, OrderItem


class SyncJobSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name', read_only=True)

    class Meta:
        model = SyncJob
        fields = ['id', 'mode', 'source', 'source_name', 'category_path', 'target_category',
                  'interval_minutes', 'batch_limit', 'pricing_policy', 'is_paused', 'next_run_at',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'source_name', 'next_run_at', 'created_at', 'updated_at']

    def validate_interval_minutes(self, value):
        if not 15 <= value <= 10080:
            raise serializers.ValidationError('Interval must be 15–10080 minutes.')
        return value

    def validate_batch_limit(self, value):
        if not 1 <= value <= 12:
            raise serializers.ValidationError('Batch limit must be 1–12.')
        return value

    def validate(self, attrs):
        unknown = set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError({'detail': 'Unknown fields: ' + ', '.join(sorted(unknown))})
        mode = attrs.get('mode', getattr(self.instance, 'mode', None))
        source = attrs.get('source', getattr(self.instance, 'source', None))
        category_path = attrs.get('category_path', getattr(self.instance, 'category_path', ''))
        target = attrs.get('target_category', getattr(self.instance, 'target_category', None))
        policy = attrs.get('pricing_policy', getattr(self.instance, 'pricing_policy', {}))
        if not isinstance(policy, dict):
            raise serializers.ValidationError({'pricing_policy': 'Must be an object.'})
        allowed = {'source_currency', 'fx_rate_to_bdt', 'fx_rate_observed_at', 'fx_max_age_hours',
                   'fee_percent', 'target_margin_percent', 'shipping_base_bdt',
                   'shipping_per_kg_bdt', 'weight_grams'}
        if set(policy) - allowed:
            raise serializers.ValidationError({'pricing_policy': 'Unknown pricing policy field.'})
        if policy:
            try:
                quote_supplier_price(100, policy)
            except ValueError as exc:
                raise serializers.ValidationError({'pricing_policy': str(exc)}) from exc
        if mode not in ('IMPORT', 'PRICE') and policy:
            raise serializers.ValidationError({'pricing_policy': 'Provider jobs do not use supplier pricing.'})
        if mode in ('IMPORT', 'PRICE'):
            if source is None or not source.is_enabled or not source.adapter_key:
                raise serializers.ValidationError({'source': 'An enabled supplier source is required.'})
            if mode == 'PRICE' and not source.sets_source_url:
                raise serializers.ValidationError({'source': 'Price jobs require a partner source.'})
            if mode == 'IMPORT':
                if not category_path or not target:
                    raise serializers.ValidationError('Import jobs require category_path and target_category.')
                from catalog.services_scrape_import import _as_relative_path
                try:
                    _as_relative_path(category_path, source.base_url)
                except ValueError as exc:
                    raise serializers.ValidationError({'category_path': str(exc)}) from exc
        elif source is not None:
            raise serializers.ValidationError({'source': 'Provider jobs do not use supplier sources.'})
        return attrs


class SyncRunSerializer(serializers.ModelSerializer):
    mode = serializers.CharField(source='job.mode', read_only=True)

    class Meta:
        model = SyncRun
        fields = ['id', 'job', 'mode', 'status', 'attempt', 'scheduled_at', 'available_at',
                  'started_at', 'finished_at', 'found_count', 'updated_count', 'skipped_count',
                  'failed_count', 'error_summary', 'result', 'created_at']


class StaffView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def forbidden(self, request):
        return None if isPlatformStaff(request.user) else renderResponse(
            data='Forbidden', message='Forbidden', status=403)


class AdminSyncJobListView(StaffView):
    def get(self, request):
        error = self.forbidden(request)
        if error: return error
        return renderResponse(data=SyncJobSerializer(SyncJob.objects.select_related('source').order_by('-id'), many=True).data,
                              message='Sync jobs retrieved')

    def post(self, request):
        error = self.forbidden(request)
        if error: return error
        serializer = SyncJobSerializer(data=request.data)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message='Validation error', status=400)
        paused = serializer.validated_data.get('is_paused', True)
        job = serializer.save(created_by=request.user,
                              next_run_at=None if paused else timezone.now())
        return renderResponse(data=SyncJobSerializer(job).data, message='Sync job created', status=201)


class AdminSyncJobDetailView(StaffView):
    def get(self, request, pk):
        error = self.forbidden(request)
        if error: return error
        job = SyncJob.objects.filter(pk=pk).first()
        if job is None: return renderResponse(data=None, message='Not found', status=404)
        return renderResponse(data=SyncJobSerializer(job).data, message='Sync job retrieved')

    def patch(self, request, pk):
        error = self.forbidden(request)
        if error: return error
        with transaction.atomic():
            job = SyncJob.objects.select_for_update().filter(pk=pk).first()
            if job is None: return renderResponse(data=None, message='Not found', status=404)
            serializer = SyncJobSerializer(job, data=request.data, partial=True)
            if not serializer.is_valid():
                return renderResponse(data=serializer.errors, message='Validation error', status=400)
            old_interval = job.interval_minutes
            old_paused = job.is_paused
            job = serializer.save()
            if job.is_paused:
                next_time = None
            elif old_paused or job.next_run_at is None:
                next_time = timezone.now()
            elif job.interval_minutes != old_interval:
                next_time = timezone.now() + timedelta(minutes=job.interval_minutes)
            else:
                next_time = job.next_run_at
            if next_time != job.next_run_at:
                job.next_run_at = next_time
                job.save(update_fields=['next_run_at', 'updated_at'])
        return renderResponse(data=SyncJobSerializer(job).data, message='Sync job updated')


class AdminSyncJobActionView(StaffView):
    def post(self, request, pk, action):
        error = self.forbidden(request)
        if error: return error
        job = SyncJob.objects.filter(pk=pk).first()
        if job is None: return renderResponse(data=None, message='Not found', status=404)
        if action == 'run':
            if job.mode in ('MERCHANT', 'ANALYTICS', 'SEARCH_CONSOLE'):
                config = provider_configuration(job.mode)
                if not config['configured']:
                    return renderResponse(data={'missing': config['missing']},
                                          message='Provider unconfigured', status=409)
            try:
                run = queue_manual(job, request.user)
            except ValueError as exc:
                return renderResponse(data={'detail': str(exc)}, message='Conflict', status=409)
            return renderResponse(data=SyncRunSerializer(run).data, message='Sync run queued', status=202)
        with transaction.atomic():
            job = SyncJob.objects.select_for_update().get(pk=pk)
            if action == 'pause':
                job.is_paused = True
                job.next_run_at = None
            elif action == 'resume':
                job.is_paused = False
                job.next_run_at = timezone.now()
            else:
                return renderResponse(data=None, message='Not found', status=404)
            job.save(update_fields=['is_paused', 'next_run_at', 'updated_at'])
        return renderResponse(data=SyncJobSerializer(job).data, message=f'Sync job {action}d')


class AdminSyncRunListView(StaffView):
    def get(self, request):
        error = self.forbidden(request)
        if error: return error
        queryset = SyncRun.objects.select_related('job').all()[:100]
        return renderResponse(data=SyncRunSerializer(queryset, many=True).data, message='Sync runs retrieved')


class AdminInsightsView(StaffView):
    def get(self, request):
        error = self.forbidden(request)
        if error: return error
        try:
            days = int(request.query_params.get('days', 30))
        except (ValueError, TypeError):
            return renderResponse(data={'days': 'Use an integer from 1–90.'},
                                  message='Validation error', status=400)
        if not 1 <= days <= 90:
            return renderResponse(data={'days': 'Use 1–90 days.'}, message='Validation error', status=400)
        since = timezone.now() - timedelta(days=days)
        sales = OrderItem.objects.filter(order__created_at__gte=since,
            order__status__in=[Order.Status.CONFIRMED, Order.Status.OUT_FOR_DELIVERY, Order.Status.DELIVERED])
        totals = sales.aggregate(total_units=Sum('quantity'), total_revenue=Sum('line_total'),
                                 total_orders=Count('order_id', distinct=True))
        velocity = list(sales.values('variant__product_id', 'product_name').annotate(
            units=Sum('quantity'), revenue=Sum('line_total')).order_by('-units')[:20])
        heatmap = list(sales.annotate(day=TruncDate('order__created_at')).values('day').annotate(
            units=Sum('quantity'), orders=Count('order_id', distinct=True),
            revenue=Sum('line_total')).order_by('day'))
        latest = {}
        for mode in ('MERCHANT', 'ANALYTICS', 'SEARCH_CONSOLE'):
            run = SyncRun.objects.filter(job__mode=mode).order_by('-created_at').first()
            config = provider_configuration(mode)
            latest[mode.lower()] = {
                'state': 'unconfigured' if not config['configured'] else ('empty' if run is None else run.status.lower()),
                'missing': config['missing'], 'last_run_at': run.finished_at if run else None,
                'result': run.result if run and run.status == SyncRun.STATUS_COMPLETED else None,
            }
        search = latest['search_console']['result'] or {}
        queries = search.get('queries', [])
        names = [set(re.findall(r'[a-z0-9]+', name.lower())) for name in
                 ProductVariant.objects.values_list('product__name', flat=True) if name]
        def covered(query):
            tokens = [token for token in re.findall(r'[a-z0-9]+', query.lower())
                      if token not in {'the', 'a', 'for', 'and', 'in', 'bd'}]
            return bool(tokens) and any(all(any(
                word == token or word.startswith(token) or token.startswith(word)
                for word in words) for token in tokens) for words in names)
        gaps = [row for row in queries if row['impressions'] >= 10 and not covered(row['query'])]
        gaps = sorted(gaps, key=lambda row: row['impressions'], reverse=True)[:20]
        logs = SyncRunSerializer(SyncRun.objects.select_related('job').all()[:20], many=True).data
        return renderResponse(data={
            'days': days, 'kpis': {
                'total_units': totals['total_units'] or 0,
                'total_revenue': totals['total_revenue'] or 0,
                'total_orders': totals['total_orders'] or 0},
            'inventory_velocity': velocity, 'sales_heatmap': heatmap,
            'conversion_funnel': (latest['analytics']['result'] or {}).get('funnel'),
            'product_funnels': (latest['analytics']['result'] or {}).get('product_funnels'),
            'search_gaps': gaps if search else None, 'sync_logs': logs, 'providers': latest,
            'inventory_state': 'available' if velocity else 'empty',
        }, message='Insights retrieved')
