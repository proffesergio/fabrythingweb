"""Staff-facing chat inbox.

Gated by IsChatStaff (see chat/permissions.py), not by a per-user ModuleUrls
row — /api/chat/ sits in core.middleware.PUBLIC_API_PREFIXES for the same
reason /api/food/ does (it mixes customer- and staff-authenticated endpoints
under one prefix), so IsChatStaff is the only thing standing between these
views and any logged-in Customer/Rider/Restaurant account.
"""
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.utils.dateparse import parse_datetime
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from chat.models import ChatMessage, ChatThread
from chat.permissions import IsChatStaff
from chat.serializers import (
    AdminChatThreadListSerializer, ChatMessageCreateSerializer, ChatMessageSerializer,
    ChatThreadStatusSerializer,
)
from chat.services import post_message
from chat.views import MAX_POLL_MESSAGES, MESSAGE_SELECT_FIELDS, _parse_after
from core.helpers import renderResponse

INBOX_FIELDS = (
    "id", "kind", "status", "related_kind", "related_id",
    "last_message_at", "created_at", "staff_unread_count",
    "customer_id", "customer__username", "customer__email",
)


class AdminChatInboxView(APIView):
    """`?status=OPEN|CLOSED` and `?kind=<Kind>` filter; always sorted by
    `-last_message_at` (ChatThread's default ordering) so the busiest/newest
    conversations surface first. select_related("customer").only(...) keeps a
    full inbox page query-bounded regardless of how many messages any thread
    holds — message bodies are never touched here."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsChatStaff]

    def get(self, request):
        qs = ChatThread.objects.select_related("customer").only(*INBOX_FIELDS)

        status = request.query_params.get("status")
        if status in ChatThread.Status.values:
            qs = qs.filter(status=status)

        kind = request.query_params.get("kind")
        if kind in ChatThread.Kind.values:
            qs = qs.filter(kind=kind)

        data = AdminChatThreadListSerializer(qs, many=True).data
        return renderResponse(data=data, message="Inbox retrieved successfully")


class AdminChatMessagesView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsChatStaff]
    throttle_scope = "chat.message"

    def get_throttles(self):
        if self.request.method == "POST":
            return [ScopedRateThrottle()]
        return []

    def get(self, request, pk):
        thread = get_object_or_404(ChatThread, pk=pk)
        qs = thread.messages.select_related("sender").only(*MESSAGE_SELECT_FIELDS)

        cursor_kind, cursor_value = _parse_after(request.query_params.get("after"))
        if cursor_kind == "id":
            messages = list(qs.filter(id__gt=cursor_value).order_by("id")[:MAX_POLL_MESSAGES])
        elif cursor_kind == "timestamp":
            messages = list(qs.filter(created_at__gt=cursor_value).order_by("id")[:MAX_POLL_MESSAGES])
        else:
            messages = list(qs.order_by("-id")[:50])
            messages.reverse()

        data = {
            "messages": ChatMessageSerializer(messages, many=True).data,
            "latest_id": messages[-1].id if messages else None,
        }
        return renderResponse(data=data, message="Messages retrieved successfully")

    def post(self, request, pk):
        thread = get_object_or_404(ChatThread, pk=pk)
        serializer = ChatMessageCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message="Validation error", status=400)

        message = post_message(
            thread, sender=request.user, sender_role=ChatMessage.SenderRole.STAFF,
            body=serializer.validated_data["body"],
        )
        return renderResponse(data=ChatMessageSerializer(message).data, message="Message sent", status=201)


class AdminChatReadView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsChatStaff]

    def post(self, request, pk):
        thread = get_object_or_404(ChatThread, pk=pk)
        thread.staff_unread_count = 0
        thread.save(update_fields=["staff_unread_count", "updated_at"])
        return renderResponse(data={"unread_count": 0}, message="Marked as read")


class AdminChatStatusView(APIView):
    """Close/reopen a thread. A closed thread still shows in the inbox
    (filterable by `?status=CLOSED`) and its messages remain readable/
    exportable — closing only stops the customer from posting new messages
    (see ChatThreadMessagesView.post)."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsChatStaff]

    def post(self, request, pk):
        thread = get_object_or_404(ChatThread, pk=pk)
        serializer = ChatThreadStatusSerializer(data=request.data)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message="Validation error", status=400)

        thread.status = serializer.validated_data["status"]
        thread.save(update_fields=["status", "updated_at"])
        return renderResponse(data={"status": thread.status}, message="Thread status updated")


class AdminChatUpdatesView(APIView):
    """Cheap staff-side badge poll — total unread across the whole inbox plus
    the threads that have any, no message bodies."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsChatStaff]

    def get(self, request):
        threads = ChatThread.objects.select_related("customer")
        total_unread = threads.aggregate(total=Sum("staff_unread_count"))["total"] or 0
        unread_threads = threads.filter(staff_unread_count__gt=0).only(*INBOX_FIELDS)

        data = {
            "total_unread": total_unread,
            "threads": AdminChatThreadListSerializer(unread_threads, many=True).data,
        }
        return renderResponse(data=data, message="Updates retrieved successfully")
