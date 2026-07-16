from django.urls import path

from .views import (
    # Public
    StoreConfigView,
    PublicCategoryListView,
    PublicHomepageView,
    PublicProductDetailView,
    PublicProductListView,
    # Customer Auth
    CustomerLoginView,
    CustomerSignupView,
    # Customer Account
    CustomerProfileView,
    ShippingAddressDetailView,
    ShippingAddressListCreateView,
    # Cart
    CartView,
    CartMergeView,
    # Customer Orders
    CustomerOrderCancelView,
    CustomerOrderDetailView,
    CustomerOrderListView,
    PlaceOrderView,
    # Reviews & Questions
    CustomerQuestionCreateView,
    CustomerReviewCreateView,
    # Admin
    AdminDashboardView,
    AdminOrderDetailView,
    AdminOrderListView,
)

urlpatterns = [
    # Public (no auth)
    path('config/', StoreConfigView.as_view(), name='store_config'),
    path('homepage/', PublicHomepageView.as_view(), name='store_homepage'),
    path('categories/', PublicCategoryListView.as_view(), name='store_categories'),
    path('products/', PublicProductListView.as_view(), name='store_products'),
    path('products/<slug:slug>/', PublicProductDetailView.as_view(), name='store_product_detail'),

    # Customer Auth
    path('auth/signup/', CustomerSignupView.as_view(), name='store_signup'),
    path('auth/login/', CustomerLoginView.as_view(), name='store_login'),

    # Customer Account (auth required)
    path('profile/', CustomerProfileView.as_view(), name='store_profile'),
    path('addresses/', ShippingAddressListCreateView.as_view(), name='store_addresses'),
    path('addresses/<int:pk>/', ShippingAddressDetailView.as_view(), name='store_address_detail'),

    # Cart (auth required)
    path('cart/', CartView.as_view(), name='store_cart'),
    path('cart/merge/', CartMergeView.as_view(), name='store_cart_merge'),

    # Customer Orders (auth required)
    path('orders/', PlaceOrderView.as_view(), name='store_place_order'),
    path('orders/list/', CustomerOrderListView.as_view(), name='store_order_list'),
    path('orders/<int:pk>/', CustomerOrderDetailView.as_view(), name='store_order_detail'),
    path('orders/<int:pk>/cancel/', CustomerOrderCancelView.as_view(), name='store_order_cancel'),

    # Reviews & Questions (auth required)
    path('reviews/', CustomerReviewCreateView.as_view(), name='store_review_create'),
    path('questions/', CustomerQuestionCreateView.as_view(), name='store_question_create'),

    # Admin endpoints
    path('admin/dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin/orders/', AdminOrderListView.as_view(), name='admin_orders'),
    path('admin/orders/<int:pk>/', AdminOrderDetailView.as_view(), name='admin_order_detail'),
]
