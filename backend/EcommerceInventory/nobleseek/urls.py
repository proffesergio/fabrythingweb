from django.urls import path

from .views import (AdConfigPublicView, ArticleDetailView, ArticleListView,
                    LatestStripView, NewsCategoryListView, NewsRssView,
                    NewsSitemapView, RelatedArticlesView)
from .views_admin import (AdminAdConfigView, AdminArticleDetailView,
                           AdminArticleListCreateView, AdminCategoryDetailView,
                           AdminCategoryListCreateView, AdminNewsOverviewView,
                           AdminNewsStatsView, AdminTrendCreateDraftView,
                           AdminTrendFetchView, AdminTrendIgnoreView,
                           AdminTrendListView)

urlpatterns = [
    # Public — mounted under /api/store/nobleseek/
    path("categories/", NewsCategoryListView.as_view(), name="ns_categories"),
    path("articles/", ArticleListView.as_view(), name="ns_articles"),
    # NOTE: <str:slug> not <slug:slug> — Django's slug converter is ASCII-only
    # ([-a-zA-Z0-9_]+) and would 404 every Bangla headline slug. str matches
    # the allow_unicode slugs unique_slug() generates.
    path("articles/<str:slug>/", ArticleDetailView.as_view(), name="ns_detail"),
    path("articles/<str:slug>/related/", RelatedArticlesView.as_view(), name="ns_related"),
    path("latest/", LatestStripView.as_view(), name="ns_latest"),
    path("sitemap-data/", NewsSitemapView.as_view(), name="ns_sitemap"),
    path("rss-data/", NewsRssView.as_view(), name="ns_rss"),
    path("ad-config/", AdConfigPublicView.as_view(), name="ns_adconfig"),
    # Admin
    path("admin/articles/", AdminArticleListCreateView.as_view(), name="ns_admin_articles"),
    path("admin/articles/<int:pk>/", AdminArticleDetailView.as_view(), name="ns_admin_article"),
    path("admin/categories/", AdminCategoryListCreateView.as_view(), name="ns_admin_cats"),
    path("admin/categories/<int:pk>/", AdminCategoryDetailView.as_view(), name="ns_admin_cat"),
    path("admin/trends/", AdminTrendListView.as_view(), name="ns_admin_trends"),
    path("admin/trends/fetch/", AdminTrendFetchView.as_view(), name="ns_admin_fetch"),
    path("admin/trends/<int:pk>/create-draft/", AdminTrendCreateDraftView.as_view(), name="ns_admin_draft"),
    path("admin/trends/<int:pk>/ignore/", AdminTrendIgnoreView.as_view(), name="ns_admin_ignore"),
    path("admin/ad-config/", AdminAdConfigView.as_view(), name="ns_admin_adconfig"),
    path("admin/stats/", AdminNewsStatsView.as_view(), name="ns_admin_stats"),
    path("admin/overview/", AdminNewsOverviewView.as_view(), name="ns_admin_overview"),
]
