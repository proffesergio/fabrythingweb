from django.urls import include, path
from .seo import sitemap
from .store_documents import store_document
from .customer_exports import AdminCustomerExportView
from .journal_bridge import JournalBridgeView
from .journal_views import JournalTopicsView, JournalRelatedView, journal_document, journal_archive_document, journal_robots

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
    CustomerTokenRefreshView,
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
    AdminCustomerListView,
    AdminDashboardView,
    AdminOrderDetailView,
    AdminOrderListView,
)
from .views_banners import (
    AdminBannerDetailView,
    AdminBannerListCreateView,
    AdminBannerReorderView,
    PublicBannerListView,
)
from .views_affiliate import (
    AdminAffiliateBulkAddView,
    AdminAffiliateDetailView,
    AdminAffiliateListCreateView,
    AdminAffiliateReorderView,
    AdminAffiliateDiagnosticView,
    AdminAffiliateParseUrlView,
    AdminAffiliateSearchView,
    AffiliateClickRedirectView,
    PublicAffiliateListView,
)

def affiliate_routes(public, click, admin, suffix=''):
    """Every affiliate route, rendered under one naming scheme.

    Called twice: once for the canonical ad-blocker-safe paths and once for
    the legacy `affiliate`/`go` ones. Building both from a single list is the
    point -- a new affiliate endpoint added to only one of two hand-written
    blocks would 404 for whichever clients are on the other scheme, and
    nothing would catch it until a customer's click earned no commission.

    `suffix` keeps the two sets' URL names distinct. The canonical set is
    registered LAST and takes the bare names, because `reverse()` resolves a
    duplicated name to the final match -- that is what makes the `go_url` in
    AffiliateProductPublicSerializer come out neutral.
    """
    return [
        path(f'{public}/', PublicAffiliateListView.as_view(),
             name=f'store_affiliate_list{suffix}'),
        path(f'{public}/<int:pk>/{click}/', AffiliateClickRedirectView.as_view(),
             name=f'store_affiliate_go{suffix}'),
        path(f'admin/{admin}/parse-url/', AdminAffiliateParseUrlView.as_view(),
             name=f'admin_affiliate_parse_url{suffix}'),
        path(f'admin/{admin}/diagnose/', AdminAffiliateDiagnosticView.as_view(),
             name=f'admin_affiliate_diagnose{suffix}'),
        path(f'admin/{admin}/search/', AdminAffiliateSearchView.as_view(),
             name=f'admin_affiliate_search{suffix}'),
        path(f'admin/{admin}/bulk-add/', AdminAffiliateBulkAddView.as_view(),
             name=f'admin_affiliate_bulk_add{suffix}'),
        path(f'admin/{admin}/reorder/', AdminAffiliateReorderView.as_view(),
             name=f'admin_affiliate_reorder{suffix}'),
        path(f'admin/{admin}/', AdminAffiliateListCreateView.as_view(),
             name=f'admin_affiliate{suffix}'),
        path(f'admin/{admin}/<int:pk>/', AdminAffiliateDetailView.as_view(),
             name=f'admin_affiliate_detail{suffix}'),
    ]


urlpatterns = [
    path('', include('storeops.urls')),
    path('documents/home/', store_document, name='store-home-document'),
    path('documents/shop/', store_document, {'kind': 'shop'}, name='store-shop-document'),
    path('documents/deals/', store_document, {'kind': 'deals'}, name='store-deals-document'),
    path('documents/product/<slug:slug>/', store_document, {'kind': 'product'}, name='store-product-document'),
    path('sitemap.xml', sitemap, name='store_sitemap'),
    # Public (no auth)
    path('config/', StoreConfigView.as_view(), name='store_config'),
    path('homepage/', PublicHomepageView.as_view(), name='store_homepage'),
    path('categories/', PublicCategoryListView.as_view(), name='store_categories'),
    path('products/', PublicProductListView.as_view(), name='store_products'),
    path('products/<slug:slug>/', PublicProductDetailView.as_view(), name='store_product_detail'),
    path('banners/', PublicBannerListView.as_view(), name='store_banners'),

    # Customer Auth
    path('auth/signup/', CustomerSignupView.as_view(), name='store_signup'),
    path('auth/login/', CustomerLoginView.as_view(), name='store_login'),
    path('auth/refresh/', CustomerTokenRefreshView.as_view(), name='store_token_refresh'),

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
    path('admin/customers/', AdminCustomerListView.as_view(), name='admin_customers'),
    path('admin/customers/export/', AdminCustomerExportView.as_view(), name='admin_customers_export'),
    path('admin/orders/', AdminOrderListView.as_view(), name='admin_orders'),
    path('admin/orders/<int:pk>/', AdminOrderDetailView.as_view(), name='admin_order_detail'),
    path('admin/banners/', AdminBannerListCreateView.as_view(), name='admin_banners'),
    path('admin/banners/reorder/', AdminBannerReorderView.as_view(), name='admin_banners_reorder'),
    path('admin/banners/<int:pk>/', AdminBannerDetailView.as_view(), name='admin_banner_detail'),
]

# Legacy first, canonical last -- see affiliate_routes() for why the order of
# these two lines decides what `go_url` looks like.
urlpatterns += affiliate_routes('affiliate', 'go', 'affiliate', suffix='_legacy')
urlpatterns += affiliate_routes('partner-picks', 'r', 'partner-picks')
urlpatterns += [
    path('journal/publish/', JournalBridgeView.as_view(), name='journal-publish'),
    path('journal/topics/', JournalTopicsView.as_view(), name='journal-topics'),
    path('journal/related/<str:slug>/', JournalRelatedView.as_view(), name='journal-related'),
    path('journal/document/<str:slug>/', journal_document, name='journal-document'),
    path('journal/archive/', journal_archive_document, name='journal-archive'),
    path('journal/archive/<slug:topic>/', journal_archive_document, name='journal-topic-archive'),
    path('robots.txt', journal_robots, name='store-robots'),
]
