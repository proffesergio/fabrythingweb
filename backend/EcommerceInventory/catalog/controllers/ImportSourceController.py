"""Admin CRUD for import sources, their category mappings, and sync history.

This is the DB-management half of the import tool -- the browse/import
endpoints in ``ProductImportController`` execute an import; these endpoints
let the owner configure *what* can be imported (add/edit a source, map its
category paths to our taxonomy, enable/disable it) and see what happened on
past runs (``ImportRun``), all without a code deploy.

Same authorization rule as every other admin catalog endpoint:
core.helpers.isPlatformStaff, never isPlatformScope alone (see
core/helpers.py's isPlatformStaff docstring for why that distinction is
load-bearing here).
"""
from rest_framework import generics, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from catalog.models import ImportRun, ImportSource, ImportSourceCategory
from core.helpers import CommonListAPIMixin, createParsedCreatedAtUpdatedAt, isPlatformStaff, renderResponse


class ImportSourceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportSourceCategory
        fields = ['id', 'source', 'source_path', 'label', 'our_category_slug', 'display_order',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ImportSourceSerializer(serializers.ModelSerializer):
    categories = ImportSourceCategorySerializer(many=True, read_only=True)

    class Meta:
        model = ImportSource
        fields = ['id', 'name', 'slug', 'base_url', 'adapter_key', 'supports_search', 'is_enabled',
                  'sets_source_url', 'notes', 'last_synced_at', 'created_at', 'updated_at', 'categories']
        read_only_fields = ['id', 'last_synced_at', 'created_at', 'updated_at']

    def validate(self, attrs):
        # Mirrors ImportSource.clean() -- a source with no adapter_key must
        # never be enabled, since there is no parser to run it through. Model
        # validation alone (clean()) only fires on a full_clean()/ModelForm
        # path, not a bare serializer .save(), so it's re-asserted here.
        is_enabled = attrs.get('is_enabled', getattr(self.instance, 'is_enabled', False))
        adapter_key = attrs.get('adapter_key', getattr(self.instance, 'adapter_key', ''))
        if is_enabled and not adapter_key:
            raise serializers.ValidationError(
                {'is_enabled': ['Cannot enable a source with no adapter_key -- add a working adapter first.']})
        return attrs


@createParsedCreatedAtUpdatedAt
class ImportRunSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name', read_only=True)
    source_slug = serializers.CharField(source='source.slug', read_only=True)
    triggered_by = serializers.SerializerMethodField()

    class Meta:
        model = ImportRun
        fields = ['id', 'source', 'source_name', 'source_slug', 'triggered_by', 'status',
                  'started_at', 'finished_at', 'found_count', 'imported_count', 'skipped_count',
                  'failed_count', 'error_summary', 'created_at', 'updated_at']

    def get_triggered_by(self, obj):
        user = obj.triggered_by_user_id
        return user.username if user else None


class AdminImportSourceListCreateView(APIView):
    """GET /api/products/admin/import/sources/ -- list every ImportSource
    (with its category mappings nested) for the admin panel's source picker
    and management view.
    POST same URL -- add a new source.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not isPlatformStaff(request.user):
            return renderResponse(data='Forbidden', message='Forbidden', status=403)
        sources = ImportSource.objects.all().prefetch_related('categories')
        return renderResponse(data=ImportSourceSerializer(sources, many=True).data, message='Sources retrieved')

    def post(self, request):
        if not isPlatformStaff(request.user):
            return renderResponse(data='Forbidden', message='Forbidden', status=403)
        serializer = ImportSourceSerializer(data=request.data)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message='Validation error', status=400)
        instance = serializer.save()
        return renderResponse(data=ImportSourceSerializer(instance).data, message='Source created', status=201)


class AdminImportSourceDetailView(APIView):
    """PATCH /api/products/admin/import/sources/<pk>/ -- edit a source
    (including flipping is_enabled). GET returns the single source."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return ImportSource.objects.filter(pk=pk).prefetch_related('categories').first()

    def get(self, request, pk):
        if not isPlatformStaff(request.user):
            return renderResponse(data='Forbidden', message='Forbidden', status=403)
        instance = self.get_object(pk)
        if instance is None:
            return renderResponse(data={'id': ['Source not found.']}, message='Validation error', status=404)
        return renderResponse(data=ImportSourceSerializer(instance).data, message='Source retrieved')

    def patch(self, request, pk):
        if not isPlatformStaff(request.user):
            return renderResponse(data='Forbidden', message='Forbidden', status=403)
        instance = self.get_object(pk)
        if instance is None:
            return renderResponse(data={'id': ['Source not found.']}, message='Validation error', status=404)
        serializer = ImportSourceSerializer(instance, data=request.data, partial=True)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message='Validation error', status=400)
        instance = serializer.save()
        return renderResponse(data=ImportSourceSerializer(instance).data, message='Source updated')


class AdminImportSourceCategoryListCreateView(APIView):
    """GET/POST /api/products/admin/import/sources/<source_pk>/categories/ --
    list or add a source-path -> our-taxonomy-slug mapping for one source.
    Several source paths may map to the same our_category_slug -- that is
    intended, not rejected as a duplicate."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, source_pk):
        if not isPlatformStaff(request.user):
            return renderResponse(data='Forbidden', message='Forbidden', status=403)
        source = ImportSource.objects.filter(pk=source_pk).first()
        if source is None:
            return renderResponse(data={'source': ['Source not found.']}, message='Validation error', status=404)
        return renderResponse(
            data=ImportSourceCategorySerializer(source.categories.all(), many=True).data,
            message='Category mappings retrieved')

    def post(self, request, source_pk):
        if not isPlatformStaff(request.user):
            return renderResponse(data='Forbidden', message='Forbidden', status=403)
        source = ImportSource.objects.filter(pk=source_pk).first()
        if source is None:
            return renderResponse(data={'source': ['Source not found.']}, message='Validation error', status=404)
        payload = {**request.data, 'source': source.id}
        serializer = ImportSourceCategorySerializer(data=payload)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message='Validation error', status=400)
        instance = serializer.save()
        return renderResponse(
            data=ImportSourceCategorySerializer(instance).data, message='Category mapping created', status=201)


class AdminImportSourceCategoryDetailView(APIView):
    """PATCH/DELETE /api/products/admin/import/source-categories/<pk>/ --
    edit or remove a single category mapping row."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return ImportSourceCategory.objects.filter(pk=pk).first()

    def patch(self, request, pk):
        if not isPlatformStaff(request.user):
            return renderResponse(data='Forbidden', message='Forbidden', status=403)
        instance = self.get_object(pk)
        if instance is None:
            return renderResponse(data={'id': ['Category mapping not found.']}, message='Validation error', status=404)
        serializer = ImportSourceCategorySerializer(instance, data=request.data, partial=True)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message='Validation error', status=400)
        instance = serializer.save()
        return renderResponse(data=ImportSourceCategorySerializer(instance).data, message='Category mapping updated')

    def delete(self, request, pk):
        if not isPlatformStaff(request.user):
            return renderResponse(data='Forbidden', message='Forbidden', status=403)
        instance = self.get_object(pk)
        if instance is None:
            return renderResponse(data={'id': ['Category mapping not found.']}, message='Validation error', status=404)
        instance.delete()
        return renderResponse(data=None, message='Category mapping deleted')


class AdminImportRunListView(generics.ListAPIView):
    """GET /api/products/admin/import/runs/?source=potakait -- sync history.
    A silent import is untrustworthy; this is how the owner sees counts and
    error summaries for past runs. Optional ?source=<slug> filters to one
    source."""
    serializer_class = ImportRunSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not isPlatformStaff(self.request.user):
            raise PermissionDenied('Staff account required.')
        queryset = ImportRun.objects.select_related('source', 'triggered_by_user_id').all()
        source_slug = self.request.query_params.get('source')
        if source_slug:
            queryset = queryset.filter(source__slug=source_slug)
        return queryset

    @CommonListAPIMixin.common_list_decorator(ImportRunSerializer)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
