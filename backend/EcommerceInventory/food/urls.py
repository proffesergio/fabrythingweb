from django.urls import path
from rest_framework.routers import DefaultRouter
from food.views_public import (
    PublicRestaurantListView, PublicRestaurantDetailView, PublicZoneListView,
)
from food.views_vendor import VendorCategoryViewSet, VendorItemViewSet

urlpatterns = [
    path("restaurants/", PublicRestaurantListView.as_view(), name="food_restaurants"),
    path("restaurants/<slug:slug>/", PublicRestaurantDetailView.as_view(), name="food_restaurant_detail"),
    path("zones/", PublicZoneListView.as_view(), name="food_zones"),
]

router = DefaultRouter()
router.register("vendor/categories", VendorCategoryViewSet, basename="vendor-categories")
router.register("vendor/items", VendorItemViewSet, basename="vendor-items")
urlpatterns += router.urls
