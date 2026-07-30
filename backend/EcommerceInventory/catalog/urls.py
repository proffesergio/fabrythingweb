from .controllers.CategoryController import CategoryListView
from .controllers.ProductController import ProductListView,ProductReviewListView,CreateProductReviewView,UpdateProductReviewView,ProductQuestionsListView,CreateProductQuestionsView,UpdateProductQuestionsView,AdminSyncPricesView,AdminProductQuickUpdateView,AdminBulkShippingFeeView
from .controllers.ProductImportController import AdminBrowseImportCandidatesView,AdminImportProductsView
from .controllers.ImportSourceController import (
    AdminImportSourceListCreateView,
    AdminImportSourceDetailView,
    AdminImportSourceCategoryListCreateView,
    AdminImportSourceCategoryDetailView,
    AdminImportRunListView,
)
from django.urls import path

urlpatterns = [
    path('categories/',CategoryListView.as_view(),name='category_list'),
    path('admin/sync-prices/',AdminSyncPricesView.as_view(),name='admin_sync_prices'),
    path('admin/shipping-fee/bulk/',AdminBulkShippingFeeView.as_view(),name='admin_bulk_shipping_fee'),
    path('admin/<int:pk>/quick-update/',AdminProductQuickUpdateView.as_view(),name='admin_product_quick_update'),
    path('admin/import/browse/',AdminBrowseImportCandidatesView.as_view(),name='admin_import_browse'),
    path('admin/import/',AdminImportProductsView.as_view(),name='admin_import_products'),
    path('admin/import/runs/',AdminImportRunListView.as_view(),name='admin_import_runs'),
    path('admin/import/sources/',AdminImportSourceListCreateView.as_view(),name='admin_import_sources'),
    path('admin/import/sources/<int:pk>/',AdminImportSourceDetailView.as_view(),name='admin_import_source_detail'),
    path('admin/import/sources/<int:source_pk>/categories/',AdminImportSourceCategoryListCreateView.as_view(),name='admin_import_source_categories'),
    path('admin/import/source-categories/<int:pk>/',AdminImportSourceCategoryDetailView.as_view(),name='admin_import_source_category_detail'),
    path('',ProductListView.as_view(),name='product_list'),
    # Product Review API List,Create,Update
    path('productReviews/<str:product_id>/',ProductReviewListView.as_view(),name='product_review_list'),
    path('createProductReview/<str:product_id>/',CreateProductReviewView.as_view(),name='product_review_create'),
    path('updateProductReview/<str:product_id>/<pk>/',UpdateProductReviewView.as_view(),name='product_review_update'),
    #Product Question API List,Create,Update
    path('productQuestions/<str:product_id>/',ProductQuestionsListView.as_view(),name='product_question_list'),
    path('createProductQuestion/<str:product_id>/',CreateProductQuestionsView.as_view(),name='product_question_create'),
    path('updateProductQuestion/<str:product_id>/<pk>/',UpdateProductQuestionsView.as_view(),name='product_question_update'),
]