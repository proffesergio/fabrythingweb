from django.urls import path

from .views import EventsView, IngestView, OverviewView, ProvidersView
from .views_overview import (FoodOverviewView, NotificationsView,
                             ShopOverviewView)

urlpatterns = [
    # Public beacon receiver (throttled, allow-listed event names only).
    path("ingest/", IngestView.as_view(), name="analytics_ingest"),
    # Staff-only admin panel API.
    path("admin/overview/", OverviewView.as_view(), name="analytics_overview"),
    path("admin/events/", EventsView.as_view(), name="analytics_events"),
    path("admin/providers/", ProvidersView.as_view(), name="analytics_providers"),
    path("admin/providers/<str:key>/", ProvidersView.as_view(), name="analytics_provider_detail"),
    # Module overview dashboards (Shop / Food) + topbar bell rollup.
    path("admin/shop-overview/", ShopOverviewView.as_view(), name="analytics_shop_overview"),
    path("admin/food-overview/", FoodOverviewView.as_view(), name="analytics_food_overview"),
    path("admin/notifications/", NotificationsView.as_view(), name="analytics_notifications"),
]
