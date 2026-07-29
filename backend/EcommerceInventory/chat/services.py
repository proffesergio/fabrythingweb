"""Shared write-path helpers for chat: posting a message (and keeping the
denormalised unread counters / last_message_at in step with it) and the
non-request-blocking WhatsApp nudge. Both customer and staff message-post
views route through ``post_message`` so the two sides can never update the
counters differently.
"""
import logging
from datetime import timedelta

from django.utils import timezone

from core.models import StoreConfiguration
from core.whatsapp import send_whatsapp_on_commit

logger = logging.getLogger("chat.services")


def post_message(thread, *, sender, sender_role, body):
    """Create a ChatMessage and update the thread's denormalised
    last_message_at + per-side unread counters in the same call, so the two
    can never drift apart.

    The side that just sent the message is, by definition, caught up on the
    thread (their own unread count resets to 0); the *other* side's unread
    count goes up by one. This is the only place either counter changes other
    than mark-read, so there is exactly one thing to get right, not one per
    view.
    """
    from chat.models import ChatMessage  # local import: avoid a module cycle at import time

    message = ChatMessage.objects.create(thread=thread, sender=sender, sender_role=sender_role, body=body)

    thread.last_message_at = message.created_at
    if sender_role == ChatMessage.SenderRole.STAFF:
        thread.customer_unread_count += 1
        thread.staff_unread_count = 0
    elif sender_role == ChatMessage.SenderRole.CUSTOMER:
        thread.staff_unread_count += 1
        thread.customer_unread_count = 0
    thread.save(update_fields=[
        "last_message_at", "customer_unread_count", "staff_unread_count", "updated_at",
    ])
    return message

# If staff replied within this window, a fresh customer message doesn't need a
# WhatsApp nudge — someone is already actively on the thread. Keeps a fast
# back-and-forth conversation from paging the admin's phone on every message.
STAFF_ACTIVE_WINDOW = timedelta(minutes=15)


def notify_admin_of_customer_message(thread, message):
    """Fire a WhatsApp alert to the admin for a customer message, unless staff
    has replied recently.

    Guarded end-to-end so a broken/unconfigured WhatsApp integration (or any
    other failure here — a bad StoreConfiguration row, a DB hiccup on the
    "recent staff reply" query) can NEVER fail the message post that triggered
    it. core.whatsapp.send_whatsapp already never raises; this wraps the rest
    (the query, the config lookup) in the same guarantee and only logs.

    Callers should invoke this after the message is committed (or at least
    after transaction.on_commit is safe to schedule against) — send_whatsapp
    itself is deferred via send_whatsapp_on_commit, so the actual HTTP call
    never runs inside an open transaction/lock.
    """
    try:
        _notify_admin_of_customer_message(thread, message)
    except Exception:  # never let a notification failure fail the request
        logger.exception(
            "chat: failed to consider/send admin WhatsApp nudge for thread %s", thread.pk
        )


def _notify_admin_of_customer_message(thread, message):
    from chat.models import ChatMessage  # local import: avoid a module cycle at import time

    recent_staff_reply = thread.messages.filter(
        sender_role=ChatMessage.SenderRole.STAFF,
        created_at__gte=timezone.now() - STAFF_ACTIVE_WINDOW,
    ).exists()
    if recent_staff_reply:
        return

    config = StoreConfiguration.get_solo()
    admin_number = config.whatsapp_admin_number
    if not admin_number:
        return

    send_whatsapp_on_commit(
        admin_number,
        kind="chat_customer_message",
        # Meta requires an approved template for any business-initiated
        # message outside the 24h service window, same constraint
        # core/whatsapp.py documents for order/rider alerts. This template
        # does not exist in Meta Business Manager yet — creating it is part
        # of turning WhatsApp alerts on at all (see docs/LIVE_CHAT.md); until
        # then is_configured() keeps every send here a no-op, same as every
        # other WhatsApp alert in the project.
        template_name="chat_new_customer_message",
        params=[thread.get_kind_display(), (message.body or "")[:200]],
        related_order=f"chat-thread-{thread.pk}",
    )
