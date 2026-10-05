from django.urls import path

from .views import (AdConfigPublicView, ArticleDetailView, ArticleListView,
                    CommentFlagView, CommentListCreateView, FlatPagePublicView,
                    LatestStripView, NewsCategoryListView, NewsRssView,
                    NewsSitemapView, PollListView, PollVoteView,
                    PushSubscribeView, RelatedArticlesView)
from .views_admin import (AdminAdConfigView, AdminArticleDetailView,
                           AdminArticleListCreateView, AdminCategoryDetailView,
                           AdminCategoryListCreateView, AdminCategoryRestoreView, AdminCommentDetailView,
                           AdminCommentListView, AdminFlatPageDetailView,
                           AdminFlatPageListCreateView, AdminNewsOverviewView,
                           AdminNewsStatsView, AdminPollDetailView,
                           AdminPollListCreateView, AdminPushCampaignListView,
                           AdminPushDeviceListView, AdminPushSendView,
                           AdminTagsView, AdminTrendCreateDraftView,
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
    path("pages/<str:slug>/", FlatPagePublicView.as_view(), name="ns_page"),
    path("comments/", CommentListCreateView.as_view(), name="ns_comments"),
    path("comments/<int:pk>/flag/", CommentFlagView.as_view(), name="ns_flag"),
    path("polls/", PollListView.as_view(), name="ns_polls"),
    path("polls/<int:pk>/vote/", PollVoteView.as_view(), name="ns_vote"),
    path("push/subscribe/", PushSubscribeView.as_view(), name="ns_push_sub"),
    # Admin
    path("admin/articles/", AdminArticleListCreateView.as_view(), name="ns_admin_articles"),
    path("admin/articles/<int:pk>/", AdminArticleDetailView.as_view(), name="ns_admin_article"),
    path("admin/categories/", AdminCategoryListCreateView.as_view(), name="ns_admin_cats"),
    path("admin/categories/restore/", AdminCategoryRestoreView.as_view(), name="ns_admin_cats_restore"),
    path("admin/categories/<int:pk>/", AdminCategoryDetailView.as_view(), name="ns_admin_cat"),
    path("admin/trends/", AdminTrendListView.as_view(), name="ns_admin_trends"),
    path("admin/trends/fetch/", AdminTrendFetchView.as_view(), name="ns_admin_fetch"),
    path("admin/trends/<int:pk>/create-draft/", AdminTrendCreateDraftView.as_view(), name="ns_admin_draft"),
    path("admin/trends/<int:pk>/ignore/", AdminTrendIgnoreView.as_view(), name="ns_admin_ignore"),
    path("admin/ad-config/", AdminAdConfigView.as_view(), name="ns_admin_adconfig"),
    path("admin/stats/", AdminNewsStatsView.as_view(), name="ns_admin_stats"),
    path("admin/overview/", AdminNewsOverviewView.as_view(), name="ns_admin_overview"),
    path("admin/tags/", AdminTagsView.as_view(), name="ns_admin_tags"),
    path("admin/pages/", AdminFlatPageListCreateView.as_view(), name="ns_admin_pages"),
    path("admin/pages/<str:slug>/", AdminFlatPageDetailView.as_view(), name="ns_admin_page"),
    path("admin/comments/", AdminCommentListView.as_view(), name="ns_admin_comments"),
    path("admin/comments/<int:pk>/", AdminCommentDetailView.as_view(), name="ns_admin_comment"),
    path("admin/push/devices/", AdminPushDeviceListView.as_view(), name="ns_admin_push_devices"),
    path("admin/push/send/", AdminPushSendView.as_view(), name="ns_admin_push_send"),
    path("admin/push/campaigns/", AdminPushCampaignListView.as_view(), name="ns_admin_push_campaigns"),
    path("admin/polls/", AdminPollListCreateView.as_view(), name="ns_admin_polls"),
    path("admin/polls/<int:pk>/", AdminPollDetailView.as_view(), name="ns_admin_poll"),
]
