"""In-house, polling-based live chat.

Deliberately NOT Django Channels / websockets / Redis / a third-party widget:
Render's free tier has no websocket support, and the chat has to attach to
*our own* rows (a store order, a food order, a future print-on-demand job) —
a third-party embed cannot do that. Clients read new messages by polling
``?after=<id>`` (see chat/views.py); nothing here pushes.

One thread model serves several purposes (``ChatThread.Kind``) rather than
one table per feature, because the polling/unread/read-tracking machinery is
identical for all of them and would otherwise be copy-pasted four times.
"""
from django.conf import settings
from django.core.validators import MaxLengthValidator
from django.db import models

from food.models import TimeStamped

MESSAGE_MAX_LENGTH = 4000


class ChatThread(TimeStamped):
    class Kind(models.TextChoices):
        GENERAL = "GENERAL", "General"
        ORDER = "ORDER", "Store Order"
        FOOD_ORDER = "FOOD_ORDER", "Food Order"
        EMERGENCY = "EMERGENCY", "Emergency Delivery"
        # Reserved for the not-yet-built print-on-demand revision conversation
        # (SP6). Nothing creates threads of this kind yet — see docs/LIVE_CHAT.md
        # for how that feature is expected to attach here.
        PRINT_JOB = "PRINT_JOB", "Print Job"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        CLOSED = "CLOSED", "Closed"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_threads",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.GENERAL)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)

    # Generic linkage to the related object WITHOUT django.contrib.contenttypes.
    # contenttypes buys polymorphic FK integrity checks and a GenericForeignKey
    # descriptor, at the cost of a join + a ContentType lookup on every access,
    # for a field this code reads at most once per thread-open (to build a
    # "Re: order #123" link) and never queries *by* in bulk. A plain
    # (short label, int) pair is enough for that and keeps ChatThread from
    # importing every app it might reference (orders, food, and eventually the
    # print-on-demand app). `related_kind` is a short dotted label such as
    # "food.FoodOrder" or "orders.SalesOrder"; `related_id` is that model's pk.
    # Both are optional — GENERAL and EMERGENCY threads usually have neither.
    related_kind = models.CharField(max_length=40, blank=True, default="")
    related_id = models.PositiveIntegerField(null=True, blank=True)

    # Denormalised so the admin inbox can `order_by("-last_message_at")`
    # without a per-row subquery/aggregate over messages (an N+1 the inbox
    # would otherwise pay on every poll).
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)

    # Unread counters per side, updated in the same request that creates a
    # message or marks a thread read (see chat/services.py). This is what
    # drives the customer badge and the admin inbox badge; deriving either by
    # scanning ChatMessage on every poll would not scale once threads have any
    # real history.
    customer_unread_count = models.PositiveIntegerField(default=0)
    staff_unread_count = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            # Admin inbox: filter by status, sort by last_message_at.
            models.Index(fields=["status", "-last_message_at"], name="chat_thread_status_lm_idx"),
            # Customer's own thread list.
            models.Index(fields=["customer", "-last_message_at"], name="chat_thread_cust_lm_idx"),
            models.Index(fields=["kind"], name="chat_thread_kind_idx"),
        ]
        ordering = ["-last_message_at", "-created_at"]

    def __str__(self):
        return f"ChatThread #{self.pk} ({self.kind}, customer={self.customer_id})"


class ChatMessage(TimeStamped):
    class SenderRole(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        STAFF = "STAFF", "Staff"
        SYSTEM = "SYSTEM", "System"

    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name="messages")
    # Nullable: a SYSTEM message (e.g. "Thread closed by staff") has no user.
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="chat_messages",
    )
    sender_role = models.CharField(max_length=10, choices=SenderRole.choices)
    # Plain text only — never rendered as HTML client-side (see docs/LIVE_CHAT.md).
    # Attachments are out of scope for this task.
    body = models.TextField(validators=[MaxLengthValidator(MESSAGE_MAX_LENGTH)])

    class Meta:
        ordering = ["id"]
        indexes = [
            # The polling query: WHERE thread_id = ? AND id > ? ORDER BY id.
            models.Index(fields=["thread", "id"], name="chat_message_thread_id_idx"),
        ]

    def __str__(self):
        return f"ChatMessage #{self.pk} in thread #{self.thread_id} ({self.sender_role})"
