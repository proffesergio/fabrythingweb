from django.urls import path
from rest_framework.routers import DefaultRouter

from printing.views import (
    AdminPrintShowcaseDetailView,
    AdminPrintShowcaseListCreateView,
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

urlpatterns = [
    # Public (no auth): the storefront "Custom Printing" form's option lists + live quote.
    path("showcase/", PrintShowcaseListView.as_view(), name="print_showcase"),
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
urlpatterns += router.urls
