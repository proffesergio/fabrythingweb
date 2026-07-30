"""
URL configuration for EcommerceInventory project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path

from core.views import index,FileUploadViewInS3,HealthView,serve_media_blob
from django.conf import settings


def api_not_found(request, *args, **kwargs):
    """Any /api/ path that fell through every route above is genuinely gone
    (e.g. the removed /api/auth/signup/), not an SPA page -- answer a real
    404 instead of falling into the `index` catch-all below, which used to
    serve 200 + index.html for ANY unmatched path including dead /api/ ones."""
    return JsonResponse({'message': 'Not Found'}, status=404)
from accounts.controllers.DynamicFormController import DynamicFormController
from accounts.controllers.SuperAdminDynamicFormController import SuperAdminDynamicFormController
from accounts.controllers.SidebarController import ModuleUrlsListAPIView, ModuleView
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/getForm/<str:modelName>/',DynamicFormController.as_view(),name='dynamicForm'),
    path('api/getForm/<str:modelName>/<str:id>/',DynamicFormController.as_view(),name='dynamicForm'),
    path('api/superAdminForm/<str:modelName>/',SuperAdminDynamicFormController.as_view(),name='superadmindynamicForm'),
    path('api/moduleUrls/',ModuleUrlsListAPIView.as_view(),name='moduleUrls_superadmin'),
    path('api/getMenus/',ModuleView.as_view(),name='sidebarmenu'),
    path('api/products/',include('catalog.urls')),
    path('api/inventory/',include('inventory.urls')),
    path('api/orders/',include('purchasing.urls')),
    # Public deploy check: reports whether the DB schema matches the shipped code.
    # See core.views.HealthView — a lagging schema is otherwise a blank 500.
    path('api/health/',HealthView.as_view(),name='health'),
    path('api/uploads/',FileUploadViewInS3.as_view(),name='fileupload'),
    # DB-backed image bytes for save_file's no-S3 fallback (core/storage.py).
    # Public: see PUBLIC_API_PREFIXES in core/middleware.py.
    path('api/media/<str:sha256>/',serve_media_blob,name='media-blob'),
    path('api/store/',include('storefront.urls')),
    path('api/food/',include('food.urls')),
    path('api/chat/',include('chat.urls')),
    path('api/print/',include('printing.urls')),
]

if settings.DEBUG:
    urlpatterns+=static(settings.STATIC_URL,document_root=settings.STATIC_ROOT)
    urlpatterns+=static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)

urlpatterns+=[
    # Only reached if none of the real api/... includes above matched.
    re_path(r'^api/.*$',api_not_found,name='api-not-found'),
    re_path(r'^(?:.*)/?$',index,name='index'),
]