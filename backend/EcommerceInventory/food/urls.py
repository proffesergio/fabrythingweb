from django.urls import path
from rest_framework.routers import DefaultRouter
from food.views_public import (
    PublicRestaurantListView, PublicRestaurantDetailView, PublicZoneListView,
)
from food.views_vendor import VendorCategoryViewSet, VendorItemViewSet, VendorRestaurantView
from food.views_admin import AdminRestaurantViewSet, AdminZoneViewSet

urlpatterns = [
    path("restaurants/", PublicRestaurantListView.as_view(), name="food_restaurants"),
    path("restaurants/<slug:slug>/", PublicRestaurantDetailView.as_view(), name="food_restaurant_detail"),
    path("zones/", PublicZoneListView.as_view(), name="food_zones"),
    # Single-object endpoint (no pk in the URL — always the caller's own restaurant),
    # so it's registered explicitly rather than via the router below.
    path("vendor/restaurant/", VendorRestaurantView.as_view(), name="food_vendor_restaurant"),
]

router = DefaultRouter()
router.register("vendor/categories", VendorCategoryViewSet, basename="vendor-categories")
router.register("vendor/items", VendorItemViewSet, basename="vendor-items")
router.register("admin/restaurants", AdminRestaurantViewSet, basename="admin-restaurants")
router.register("admin/zones", AdminZoneViewSet, basename="admin-zones")
urlpatterns += router.urls
