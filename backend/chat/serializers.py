from rest_framework import serializers

from chat.models import MESSAGE_MAX_LENGTH, ChatMessage, ChatThread


class ChatMessageSerializer(serializers.ModelSerializer):
    """Read shape for a single message. `body` is plain text — the frontend
    must render it as text (never dangerouslySetInnerHTML); nothing here
    escapes/sanitises HTML because nothing is ever interpreted as HTML."""

    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = ["id", "thread_id", "sender_id", "sender_role", "sender_name", "body", "created_at"]
        read_only_fields = fields

    def get_sender_name(self, obj):
        if obj.sender_id and obj.sender:
            return getattr(obj.sender, "username", None) or getattr(obj.sender, "email", None)
        return None


class ChatMessageCreateSerializer(serializers.Serializer):
    body = serializers.CharField(
        max_length=MESSAGE_MAX_LENGTH, allow_blank=False, trim_whitespace=True,
    )


class ChatThreadCreateSerializer(serializers.Serializer):
    """Opens a thread with its first message in one call — a thread with zero
    messages is not a useful state to expose through the API."""

    kind = serializers.ChoiceField(choices=ChatThread.Kind.choices, default=ChatThread.Kind.GENERAL)
    related_kind = serializers.CharField(max_length=40, required=False, allow_blank=True, default="")
    related_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    body = serializers.CharField(
        max_length=MESSAGE_MAX_LENGTH, allow_blank=False, trim_whitespace=True,
    )


class ChatThreadListSerializer(serializers.ModelSerializer):
    """Customer-facing thread list/detail — no staff-only fields."""

    unread_count = serializers.IntegerField(source="customer_unread_count", read_only=True)

    class Meta:
        model = ChatThread
        fields = [
            "id", "kind", "status", "related_kind", "related_id",
            "last_message_at", "created_at", "unread_count",
        ]
        read_only_fields = fields


class AdminChatThreadListSerializer(serializers.ModelSerializer):
    """Inbox row — cheap by design (no message bodies, see the polling note in
    chat/views_admin.py). `select_related("customer")` in the view keeps this
    query-bounded across a page of threads."""

    unread_count = serializers.IntegerField(source="staff_unread_count", read_only=True)
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = ChatThread
        fields = [
            "id", "kind", "status", "related_kind", "related_id",
            "customer_id", "customer_name",
            "last_message_at", "created_at", "unread_count",
        ]
        read_only_fields = fields

    def get_customer_name(self, obj):
        return getattr(obj.customer, "username", None) or getattr(obj.customer, "email", None)


class ChatThreadStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ChatThread.Status.choices)
