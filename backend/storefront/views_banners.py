"""Homepage hero banner endpoints.

Public: `GET /api/store/banners/` -- active, in-window banners for the
storefront hero, already ordered for direct rendering.

Admin: full CRUD + reorder under `/api/store/admin/banners/`, gated by
`IsPlatformStaff` (see storefront/permissions.py) because `/api/store/` sits
in `core.middleware.PUBLIC_API_PREFIXES` -- PermissionMiddleware's ModuleUrls
gate never runs for it, so that permission class is the only thing standing
between banner CRUD and any logged-in Customer account.
"""
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.helpers import renderResponse

from .models import Banner
from .permissions import IsPlatformStaff
from .serializers import BannerAdminSerializer, BannerPublicSerializer


class PublicBannerListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        banners = Banner.objects.active().select_related('cta_product')
        data = BannerPublicSerializer(banners, many=True, context={'request': request}).data
        return renderResponse(data=data, message='Banners retrieved successfully')


class AdminBannerListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPlatformStaff]

    def get(self, request):
        banners = Banner.objects.all().select_related('cta_product')
        data = BannerAdminSerializer(banners, many=True).data
        return renderResponse(data=data, message='Banners retrieved successfully')

    def post(self, request):
        serializer = BannerAdminSerializer(data=request.data)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message='Validation error', status=400)
        serializer.save()
        return renderResponse(data=serializer.data, message='Banner created', status=201)


class AdminBannerDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPlatformStaff]

    def get(self, request, pk):
        banner = get_object_or_404(Banner, pk=pk)
        return renderResponse(data=BannerAdminSerializer(banner).data, message='Banner retrieved')

    def patch(self, request, pk):
        banner = get_object_or_404(Banner, pk=pk)
        serializer = BannerAdminSerializer(banner, data=request.data, partial=True)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message='Validation error', status=400)
        serializer.save()
        return renderResponse(data=serializer.data, message='Banner updated')

    def put(self, request, pk):
        return self.patch(request, pk)

    def delete(self, request, pk):
        banner = get_object_or_404(Banner, pk=pk)
        banner.delete()
        return renderResponse(data=None, message='Banner deleted')


class AdminBannerReorderView(APIView):
    """`POST {"order": [id, id, id, ...]}` in the desired display order --
    sets `display_order` to each id's position. Wrapped in one transaction so
    a reorder can never land half-applied."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsPlatformStaff]

    def post(self, request):
        order = request.data.get('order')
        if not isinstance(order, list) or not order:
            return renderResponse(
                data='`order` must be a non-empty list of banner ids',
                message='Validation error', status=400,
            )

        with transaction.atomic():
            for index, banner_id in enumerate(order):
                Banner.objects.filter(pk=banner_id).update(display_order=index)

        banners = Banner.objects.all().select_related('cta_product')
        return renderResponse(data=BannerAdminSerializer(banners, many=True).data, message='Banners reordered')
