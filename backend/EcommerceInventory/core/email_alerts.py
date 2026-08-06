"""Email provider for admin alerts — the one channel that is live today.

Deliberately the same contract as ``core.whatsapp``: never raises, no-ops on a
blank destination, and offers an ``_on_commit`` variant for callers holding row
locks. The difference is intent — WhatsApp and SMS ship *dormant* pending
credentials, whereas email is the owner's actual notification channel, so a
send here is expected to happen on every real order.

SMTP credentials come from the environment (see ``config/settings/base.py``);
the destination mailbox is a low-stakes setting and lives in
``core.models.StoreConfiguration.alert_email`` so it can be changed from the
admin panel without a redeploy — the same split ``core.whatsapp`` documents for
its token vs. its destination number.

When no SMTP credentials are set, Django is pointed at the console backend, so
this module still "sends" (into the logs) rather than erroring. That keeps
local development and the pre-credential production window honest: the alert
path is exercised, it just doesn't leave the box.
"""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

logger = logging.getLogger("core.email_alerts")


def send_email_alert(to, *, kind, subject, body, related_order=""):
    """Send one admin alert email. Returns True/False; **never raises**.

    A failure here must never propagate: the only callers are order-placement
    and dispatch paths, and losing a paying customer's order because Gmail
    refused a connection would be a far worse outcome than a missed alert.
    """
    if not to:
        logger.info("email: skipping %s alert — no destination address configured", kind)
        return False

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[to],
            fail_silently=False,
        )
    except Exception as exc:  # SMTP down, auth rejected, DNS failure, ...
        logger.warning("email: %s alert to %s failed (order %s): %s: %s",
                       kind, to, related_order or "-", type(exc).__name__, exc)
        return False

    logger.info("email: sent %s alert to %s (order %s)", kind, to, related_order or "-")
    return True


def send_email_alert_on_commit(to, **kwargs):
    """Defer ``send_email_alert`` until after the current transaction commits.

    Same reasoning as ``core.whatsapp.send_whatsapp_on_commit``: order
    placement runs inside ``@transaction.atomic`` while holding
    ``select_for_update()`` locks on variant rows, and SMTP is a blocking
    network call. Sending inline would hold those locks for the duration of
    the handshake and let a slow mail server serialise checkout.
    """
    transaction.on_commit(lambda: send_email_alert(to, **kwargs))
