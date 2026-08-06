"""SMS provider for admin/customer alerts — ships built but dormant.

Same "ships dormant" contract as ``core.whatsapp``: fully wired, fully tested,
and completely inert (no network calls, no exceptions) until ``SMS_API_KEY``
and ``SMS_SENDER_ID`` are present in the environment. The owner will supply
these later; until then email (``core.email_alerts``) carries every alert.

Deliberately provider-agnostic. The Bangladeshi gateways the owner is choosing
between (bulksmsbd, Alpha Net, MIM SMS, …) all expose the same shape — an HTTP
GET/POST with an api key, a sender id, a msisdn and a text body — so the
endpoint is a single env var rather than a vendor-specific client library.
Point ``SMS_API_URL`` at the gateway and set the credentials; nothing else in
this module needs to change.

Credentials come from the environment only, never the database, and are never
logged: the parameters are logged by *name* on failure, never by value.
"""
import logging
import os

import requests
from django.db import transaction

logger = logging.getLogger("core.sms")

REQUEST_TIMEOUT_SECONDS = 5
DEFAULT_API_URL = "https://api.sms.net.bd/sendsms"


def _api_key():
    return os.getenv("SMS_API_KEY")


def _sender_id():
    return os.getenv("SMS_SENDER_ID")


def _api_url():
    return os.getenv("SMS_API_URL", DEFAULT_API_URL)


def is_configured():
    """True once both credentials are present. Everything else here no-ops
    until this is true — that is the whole dormant contract."""
    return bool(_api_key() and _sender_id())


def send_sms(to, *, kind, body, related_order=""):
    """Send one SMS. Returns True/False; **never raises**.

    No-op (returns False, no network call) when ``to`` is blank or the
    provider is unconfigured — those are the expected dormant states, not
    failures worth alarming about.
    """
    if not to:
        logger.info("sms: skipping %s alert — no destination number configured", kind)
        return False
    if not is_configured():
        logger.info("sms: skipping %s alert to %s — provider not configured", kind, to)
        return False

    try:
        response = requests.post(
            _api_url(),
            data={"api_key": _api_key(), "sender_id": _sender_id(), "msisdn": to, "message": body},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if not response.ok:
            logger.warning("sms: %s alert to %s failed (order %s): HTTP %s",
                           kind, to, related_order or "-", response.status_code)
            return False
    except Exception as exc:  # network error, timeout, DNS failure, ...
        logger.warning("sms: %s alert to %s failed (order %s): %s: %s",
                       kind, to, related_order or "-", type(exc).__name__, exc)
        return False

    return True


def send_sms_on_commit(to, **kwargs):
    """Defer ``send_sms`` until after the current transaction commits — same
    lock-holding reasoning as ``core.whatsapp.send_whatsapp_on_commit``."""
    transaction.on_commit(lambda: send_sms(to, **kwargs))
