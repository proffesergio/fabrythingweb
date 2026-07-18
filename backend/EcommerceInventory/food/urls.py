from django.urls import path
from food.views_public import (
    PublicRestaurantListView, PublicRestaurantDetailView, PublicZoneListView,
)

urlpatterns = [
    path("restaurants/", PublicRestaurantListView.as_view(), name="food_restaurants"),
    path("restaurants/<slug:slug>/", PublicRestaurantDetailView.as_view(), name="food_restaurant_detail"),
    path("zones/", PublicZoneListView.as_view(), name="food_zones"),
]
