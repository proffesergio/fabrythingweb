from django.urls import path

from chat.views import (
    ChatThreadListCreateView, ChatThreadMessagesView, ChatThreadReadView, ChatUpdatesView,
)
from chat.views_admin import (
    AdminChatInboxView, AdminChatMessagesView, AdminChatReadView, AdminChatStatusView,
    AdminChatUpdatesView,
)

urlpatterns = [
    # Customer side
    path("threads/", ChatThreadListCreateView.as_view(), name="chat_threads"),
    path("threads/updates/", ChatUpdatesView.as_view(), name="chat_updates"),
    path("threads/<int:pk>/messages/", ChatThreadMessagesView.as_view(), name="chat_thread_messages"),
    path("threads/<int:pk>/read/", ChatThreadReadView.as_view(), name="chat_thread_read"),
    # Staff side
    path("admin/threads/", AdminChatInboxView.as_view(), name="chat_admin_threads"),
    path("admin/threads/updates/", AdminChatUpdatesView.as_view(), name="chat_admin_updates"),
    path("admin/threads/<int:pk>/messages/", AdminChatMessagesView.as_view(), name="chat_admin_thread_messages"),
    path("admin/threads/<int:pk>/read/", AdminChatReadView.as_view(), name="chat_admin_thread_read"),
    path("admin/threads/<int:pk>/status/", AdminChatStatusView.as_view(), name="chat_admin_thread_status"),
]
