from django.urls import path
from rest_framework.routers import DefaultRouter

from printing.views import (
    AdminPrintShowcaseDetailView,
    AdminPrintShowcaseListCreateView,
    AdminPrintShowcaseUploadView,
    PrintShowcaseListView,
    PrintablePresetListView, PrintAreaListView, PrintProofDecisionView, PrintQuoteView,
    PrintReferenceImageUploadView, PrintRequestDetailView, PrintRequestListCreateView,
    PrintRosterLineDetailView, PrintRosterLineListCreateView,
)
from printing.views_admin import (
    AdminPrintAreaViewSet, AdminPrintablePresetViewSet, AdminPrintExportView, AdminPrintPriceView,
    AdminPrintPricingConfigView, AdminPrintProofCreateView, AdminPrintRequestDetailView,
    AdminPrintRequestQueueView, AdminPrintStatusView,
)
from printing.views_press import (
    AdminCorporateViewSet, AdminFinishingViewSet, AdminPaperStockViewSet,
    AdminPressOrderDetailView, AdminPressOrderQueueView, AdminPressExportView,
    AdminPressPaymentView, AdminPressProductViewSet, AdminPressShippingViewSet,
    AdminPressShopConfigView, AdminPressSizeViewSet, AdminPressStatusView,
    AdminQuotationQueueView, PressArtworkUploadView, PressCheckoutView,
    PressConfigView, PressFinishingListView, PressOrderDetailView, PressOrderListView,
    PressPaperListView, PressPaymentCallbackView, PressPaymentInitView,
    PressProductDetailView, PressProductListView, PressQuotationListCreateView,
    PressQuoteView,
)

urlpatterns = [
    # Public (no auth): the storefront "Custom Printing" form's option lists + live quote.
    path("showcase/", PrintShowcaseListView.as_view(), name="print_showcase"),
    path("admin/showcase/upload/", AdminPrintShowcaseUploadView.as_view(), name="admin_print_showcase_upload"),
    path("admin/showcase/", AdminPrintShowcaseListCreateView.as_view(), name="admin_print_showcase"),
    path("admin/showcase/<int:pk>/", AdminPrintShowcaseDetailView.as_view(), name="admin_print_showcase_detail"),
    path("presets/", PrintablePresetListView.as_view(), name="print_presets"),
    path("print-areas/", PrintAreaListView.as_view(), name="print_areas"),
    path("quote/", PrintQuoteView.as_view(), name="print_quote"),

    # Customer side
    path("requests/", PrintRequestListCreateView.as_view(), name="print_requests"),
    path("requests/<int:pk>/", PrintRequestDetailView.as_view(), name="print_request_detail"),
    path("requests/<int:pk>/reference-images/", PrintReferenceImageUploadView.as_view(), name="print_request_reference_images"),
    path("requests/<int:pk>/roster/", PrintRosterLineListCreateView.as_view(), name="print_request_roster"),
    path("requests/<int:pk>/roster/<int:line_pk>/", PrintRosterLineDetailView.as_view(), name="print_request_roster_detail"),
    path("requests/<int:pk>/proofs/<int:proof_pk>/decision/", PrintProofDecisionView.as_view(), name="print_proof_decision"),

    # ── Web-to-press engine (ColorLifePrint-style) ──
    # Public catalogue + live calculator.
    path("press/products/", PressProductListView.as_view(), name="press_products"),
    path("press/products/<slug:slug>/", PressProductDetailView.as_view(), name="press_product_detail"),
    path("press/paper/", PressPaperListView.as_view(), name="press_paper"),
    path("press/finishing/", PressFinishingListView.as_view(), name="press_finishing"),
    path("press/quote/", PressQuoteView.as_view(), name="press_quote"),
    path("press/config/", PressConfigView.as_view(), name="press_config"),
    # Customer checkout + orders.
    path("press/checkout/", PressCheckoutView.as_view(), name="press_checkout"),
    path("press/orders/", PressOrderListView.as_view(), name="press_orders"),
    path("press/orders/<int:pk>/", PressOrderDetailView.as_view(), name="press_order_detail"),
    path("press/orders/<int:pk>/artwork/", PressArtworkUploadView.as_view(), name="press_order_artwork"),
    path("press/orders/<int:pk>/pay/", PressPaymentInitView.as_view(), name="press_order_pay"),
    path("press/orders/<int:pk>/pay/callback/", PressPaymentCallbackView.as_view(), name="press_order_pay_callback"),
    path("press/quotations/", PressQuotationListCreateView.as_view(), name="press_quotations"),
    # Staff press surface.
    path("press/admin/orders/", AdminPressOrderQueueView.as_view(), name="admin_press_orders"),
    path("press/admin/orders/<int:pk>/", AdminPressOrderDetailView.as_view(), name="admin_press_order_detail"),
    path("press/admin/orders/<int:pk>/status/", AdminPressStatusView.as_view(), name="admin_press_order_status"),
    path("press/admin/orders/<int:pk>/payment/", AdminPressPaymentView.as_view(), name="admin_press_order_payment"),
    path("press/admin/orders/<int:pk>/export/", AdminPressExportView.as_view(), name="admin_press_order_export"),
    path("press/admin/shop-config/", AdminPressShopConfigView.as_view(), name="admin_press_shop_config"),
    path("press/admin/quotations/", AdminQuotationQueueView.as_view(), name="admin_press_quotations"),

    # Staff side
    path("admin/requests/", AdminPrintRequestQueueView.as_view(), name="admin_print_requests"),
    path("admin/requests/<int:pk>/", AdminPrintRequestDetailView.as_view(), name="admin_print_request_detail"),
    path("admin/requests/<int:pk>/proofs/", AdminPrintProofCreateView.as_view(), name="admin_print_request_proofs"),
    path("admin/requests/<int:pk>/price/", AdminPrintPriceView.as_view(), name="admin_print_request_price"),
    path("admin/requests/<int:pk>/status/", AdminPrintStatusView.as_view(), name="admin_print_request_status"),
    path("admin/requests/<int:pk>/export/", AdminPrintExportView.as_view(), name="admin_print_request_export"),
    path("admin/pricing/", AdminPrintPricingConfigView.as_view(), name="admin_print_pricing_config"),
]

router = DefaultRouter()
router.register("admin/print-areas", AdminPrintAreaViewSet, basename="admin-print-areas")
router.register("admin/presets", AdminPrintablePresetViewSet, basename="admin-print-presets")
router.register("press/admin/products", AdminPressProductViewSet, basename="admin-press-products")
router.register("press/admin/sizes", AdminPressSizeViewSet, basename="admin-press-sizes")
router.register("press/admin/paper", AdminPaperStockViewSet, basename="admin-press-paper")
router.register("press/admin/finishing", AdminFinishingViewSet, basename="admin-press-finishing")
router.register("press/admin/shipping", AdminPressShippingViewSet, basename="admin-press-shipping")
router.register("press/admin/corporate", AdminCorporateViewSet, basename="admin-press-corporate")
urlpatterns += router.urls
