from django.urls import path

from .views import EventsView, IngestView, OverviewView, ProvidersView

urlpatterns = [
    # Public beacon receiver (throttled, allow-listed event names only).
    path("ingest/", IngestView.as_view(), name="analytics_ingest"),
    # Staff-only admin panel API.
    path("admin/overview/", OverviewView.as_view(), name="analytics_overview"),
    path("admin/events/", EventsView.as_view(), name="analytics_events"),
    path("admin/providers/", ProvidersView.as_view(), name="analytics_providers"),
    path("admin/providers/<str:key>/", ProvidersView.as_view(), name="analytics_provider_detail"),
]
