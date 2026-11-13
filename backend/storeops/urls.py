from django.urls import path

from .views import ImageActionView, OperationsView, QueueImagesView, whatsapp_webhook

urlpatterns = [
    path("admin/operations/", OperationsView.as_view(), name="store-operations"),
    path(
        "admin/operations/images/", QueueImagesView.as_view(), name="store-images-queue"
    ),
    path(
        "admin/operations/images/<int:pk>/<str:action>/",
        ImageActionView.as_view(),
        name="store-image-action",
    ),
    path("webhooks/whatsapp/", whatsapp_webhook, name="store-whatsapp-webhook"),
]
