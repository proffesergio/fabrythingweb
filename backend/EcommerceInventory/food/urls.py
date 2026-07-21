from django.urls import path
from rest_framework.routers import DefaultRouter
from food.views_public import (
    PublicRestaurantListView, PublicRestaurantDetailView, PublicZoneListView,
)
from food.views_vendor import VendorCategoryViewSet, VendorItemViewSet, VendorRestaurantView
from food.views_admin import AdminRestaurantViewSet, AdminZoneViewSet
from food.views_admin_menu import (
    AdminCategoryViewSet, AdminItemViewSet, AdminOptionGroupViewSet, AdminOptionViewSet,
)
from food.views_orders import (
    FoodOrderView, FoodOrderTrackView, VendorOrderListView, VendorOrderStatusView,
    AdminFoodOrderListView, AdminFoodOrderStatusView, AdminFoodOrderDetailView,
)
from food.views_admin_dashboard import AdminFoodDashboardView
from food.views_food_ext import (
    VendorCouponViewSet, AdminCouponViewSet, CouponValidateView, AdminRiderViewSet,
    AdminAssignRiderView, RiderMeView, RiderAvailabilityView, RiderOrdersView,
    RiderOrderStatusView, NotificationView, LoyaltyView, AdminPaymentListView,
    RiderHeartbeatView, RiderEarningsView,
)
from food.views_menu_copy import AdminMenuCopyView
from food.views_settlement import (
    AdminSettlementListView, AdminSettlementSummaryView, AdminSettlementLegView,
    AdminSettlementBulkLegView, AdminZoneTreeView, AdminVillageViewSet,
)

urlpatterns = [
    path("restaurants/", PublicRestaurantListView.as_view(), name="food_restaurants"),
    path("restaurants/<slug:slug>/", PublicRestaurantDetailView.as_view(), name="food_restaurant_detail"),
    path("zones/", PublicZoneListView.as_view(), name="food_zones"),
    # Single-object endpoint (no pk in the URL — always the caller's own restaurant),
    # so it's registered explicitly rather than via the router below.
    path("vendor/restaurant/", VendorRestaurantView.as_view(), name="food_vendor_restaurant"),
    # Orders — customer (guest/auth), vendor fulfillment, admin oversight.
    path("orders/", FoodOrderView.as_view(), name="food_orders"),
    path("orders/<str:order_code>/", FoodOrderTrackView.as_view(), name="food_order_track"),
    path("vendor/orders/", VendorOrderListView.as_view(), name="food_vendor_orders"),
    path("vendor/orders/<int:pk>/status/", VendorOrderStatusView.as_view(), name="food_vendor_order_status"),
    path("admin/dashboard/", AdminFoodDashboardView.as_view(), name="food_admin_dashboard"),
    path("admin/orders/", AdminFoodOrderListView.as_view(), name="food_admin_orders"),
    path("admin/orders/<int:pk>/", AdminFoodOrderDetailView.as_view(), name="food_admin_order_detail"),
    path("admin/orders/<int:pk>/status/", AdminFoodOrderStatusView.as_view(), name="food_admin_order_status"),
    # Phase A–D features
    path("coupons/validate/", CouponValidateView.as_view(), name="food_coupon_validate"),
    path("admin/orders/<int:pk>/assign/", AdminAssignRiderView.as_view(), name="food_admin_assign_rider"),
    path("admin/payments/", AdminPaymentListView.as_view(), name="food_admin_payments"),
    # Settlement ledger — the Payments tab's real data source.
    path("admin/settlements/", AdminSettlementListView.as_view(), name="food_admin_settlements"),
    path("admin/settlements/summary/", AdminSettlementSummaryView.as_view(), name="food_admin_settlement_summary"),
    path("admin/settlements/bulk/", AdminSettlementBulkLegView.as_view(), name="food_admin_settlement_bulk"),
    path("admin/settlements/<int:pk>/leg/", AdminSettlementLegView.as_view(), name="food_admin_settlement_leg"),
    path("admin/zone-tree/", AdminZoneTreeView.as_view(), name="food_admin_zone_tree"),
    path("admin/menu/copy/", AdminMenuCopyView.as_view(), name="food_admin_menu_copy"),
    path("rider/me/", RiderMeView.as_view(), name="food_rider_me"),
    path("rider/availability/", RiderAvailabilityView.as_view(), name="food_rider_availability"),
    path("rider/heartbeat/", RiderHeartbeatView.as_view(), name="food_rider_heartbeat"),
    path("rider/orders/", RiderOrdersView.as_view(), name="food_rider_orders"),
    path("rider/earnings/", RiderEarningsView.as_view(), name="food_rider_earnings"),
    path("rider/orders/<int:pk>/status/", RiderOrderStatusView.as_view(), name="food_rider_order_status"),
    path("notifications/", NotificationView.as_view(), name="food_notifications"),
    path("loyalty/", LoyaltyView.as_view(), name="food_loyalty"),
]

router = DefaultRouter()
router.register("vendor/categories", VendorCategoryViewSet, basename="vendor-categories")
router.register("vendor/items", VendorItemViewSet, basename="vendor-items")
router.register("admin/restaurants", AdminRestaurantViewSet, basename="admin-restaurants")
router.register("admin/zones", AdminZoneViewSet, basename="admin-zones")
router.register("admin/categories", AdminCategoryViewSet, basename="admin-categories")
router.register("admin/items", AdminItemViewSet, basename="admin-items")
router.register("admin/option-groups", AdminOptionGroupViewSet, basename="admin-option-groups")
router.register("admin/options", AdminOptionViewSet, basename="admin-options")
router.register("vendor/coupons", VendorCouponViewSet, basename="vendor-coupons")
router.register("admin/coupons", AdminCouponViewSet, basename="admin-coupons")
router.register("admin/riders", AdminRiderViewSet, basename="admin-riders")
router.register("admin/villages", AdminVillageViewSet, basename="admin-villages")
urlpatterns += router.urls
