"""Customer-facing chat endpoints.

Every view here scopes to `customer=request.user` — a customer may only ever
read or post to their OWN threads. Getting this wrong is exactly the kind of
cross-tenant bug this project has shipped before (see
accounts/test_dynamic_form_scope.py); chat/tests/test_customer_api.py pins it
explicitly for both read and write.

The messages endpoint is the polling-critical one: `?after=<message id or ISO
timestamp>` returns only the messages newer than that cursor, never the whole
thread history, and the query is select_related/only()-bounded so a poll never
costs more than a couple of indexed lookups regardless of thread age.
"""
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.utils.dateparse import parse_datetime
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from chat.models import ChatMessage, ChatThread
from chat.serializers import (
    ChatMessageCreateSerializer, ChatMessageSerializer, ChatThreadCreateSerializer,
    ChatThreadListSerializer,
)
from chat.services import notify_admin_of_customer_message, post_message
from core.helpers import renderResponse

# Initial page of a thread (no `after`): most recent N messages. A poll that
# *does* pass `after` has no cap other than MAX_POLL_MESSAGES below — it's
# already bounded to "new since last poll", which in normal use is a handful.
INITIAL_PAGE_SIZE = 50
# Safety cap even on an `after` query, so a client that went quiet for a very
# long time (or sends a stale/garbage cursor) can't pull an unbounded result.
MAX_POLL_MESSAGES = 200

MESSAGE_SELECT_FIELDS = (
    "id", "thread_id", "sender_id", "sender_role", "body", "created_at",
    "sender__username", "sender__email",
)

THREAD_LIST_FIELDS = (
    "id", "kind", "status", "related_kind", "related_id",
    "last_message_at", "created_at", "customer_unread_count", "customer_id",
)


def _parse_after(raw):
    """`after` is either a ChatMessage id (int) or an ISO timestamp. Returns
    (kind, value) or (None, None) if it doesn't parse as either — callers treat
    that as "no cursor" rather than 500ing a poll on a malformed query param."""
    if raw is None or raw == "":
        return None, None
    try:
        return "id", int(raw)
    except (TypeError, ValueError):
        pass
    parsed = parse_datetime(raw)
    if parsed is not None:
        return "timestamp", parsed
    return None, None


class ChatThreadListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_scope = "chat.message"

    def get_throttles(self):
        # Only throttle the write path (opening a thread). Reading the thread
        # list is cheap and, on the badge/idle poll cadence, must not be
        # rate-limited the same way spammy posting is.
        if self.request.method == "POST":
            return [ScopedRateThrottle()]
        return []

    def get(self, request):
        threads = ChatThread.objects.filter(customer=request.user).only(*THREAD_LIST_FIELDS)
        data = ChatThreadListSerializer(threads, many=True).data
        return renderResponse(data=data, message="Threads retrieved successfully")

    def post(self, request):
        serializer = ChatThreadCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message="Validation error", status=400)

        v = serializer.validated_data
        thread = ChatThread.objects.create(
            customer=request.user,
            kind=v["kind"],
            related_kind=v.get("related_kind", ""),
            related_id=v.get("related_id"),
        )
        message = post_message(
            thread, sender=request.user, sender_role=ChatMessage.SenderRole.CUSTOMER, body=v["body"],
        )
        notify_admin_of_customer_message(thread, message)

        data = ChatThreadListSerializer(thread).data
        data["message"] = ChatMessageSerializer(message).data
        return renderResponse(data=data, message="Thread created successfully", status=201)


class ChatThreadMessagesView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_scope = "chat.message"

    def get_throttles(self):
        if self.request.method == "POST":
            return [ScopedRateThrottle()]
        return []

    def _get_owned_thread(self, request, pk):
        # A customer's own thread only — anyone else's pk 404s, for both this
        # GET and the POST below (never 403; existence of another customer's
        # thread id is not information this endpoint reveals either).
        return get_object_or_404(ChatThread, pk=pk, customer=request.user)

    def get(self, request, pk):
        thread = self._get_owned_thread(request, pk)
        qs = thread.messages.select_related("sender").only(*MESSAGE_SELECT_FIELDS)

        cursor_kind, cursor_value = _parse_after(request.query_params.get("after"))
        if cursor_kind == "id":
            messages = list(qs.filter(id__gt=cursor_value).order_by("id")[:MAX_POLL_MESSAGES])
        elif cursor_kind == "timestamp":
            messages = list(qs.filter(created_at__gt=cursor_value).order_by("id")[:MAX_POLL_MESSAGES])
        else:
            # No cursor: initial load — most recent page, oldest first.
            messages = list(qs.order_by("-id")[:INITIAL_PAGE_SIZE])
            messages.reverse()

        data = {
            "messages": ChatMessageSerializer(messages, many=True).data,
            "latest_id": messages[-1].id if messages else None,
        }
        return renderResponse(data=data, message="Messages retrieved successfully")

    def post(self, request, pk):
        thread = self._get_owned_thread(request, pk)
        if thread.status == ChatThread.Status.CLOSED:
            return renderResponse(data="This conversation is closed.", message="Thread is closed", status=400)

        serializer = ChatMessageCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return renderResponse(data=serializer.errors, message="Validation error", status=400)

        message = post_message(
            thread, sender=request.user, sender_role=ChatMessage.SenderRole.CUSTOMER,
            body=serializer.validated_data["body"],
        )
        notify_admin_of_customer_message(thread, message)
        return renderResponse(data=ChatMessageSerializer(message).data, message="Message sent", status=201)


class ChatThreadReadView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        thread = get_object_or_404(ChatThread, pk=pk, customer=request.user)
        thread.customer_unread_count = 0
        thread.save(update_fields=["customer_unread_count", "updated_at"])
        return renderResponse(data={"unread_count": 0}, message="Marked as read")


class ChatUpdatesView(APIView):
    """Cheap badge poll: total unread + a lightweight per-thread list, no
    message bodies and no join beyond the thread row itself. Meant to be
    polled far more often (and while the chat panel is closed) than the full
    message-fetch endpoint above — see docs/LIVE_CHAT.md for the intervals."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        threads = ChatThread.objects.filter(customer=request.user)
        total_unread = threads.aggregate(total=Sum("customer_unread_count"))["total"] or 0
        unread_threads = threads.filter(customer_unread_count__gt=0).only(*THREAD_LIST_FIELDS)

        data = {
            "total_unread": total_unread,
            "threads": ChatThreadListSerializer(unread_threads, many=True).data,
        }
        return renderResponse(data=data, message="Updates retrieved successfully")
