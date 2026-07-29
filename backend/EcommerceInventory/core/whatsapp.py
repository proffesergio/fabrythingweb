"""Meta WhatsApp Cloud API provider — ships built but dormant.

The owner has chosen the official Meta WhatsApp Cloud API for order/rider
alerts but does not have Meta Business verification yet. Everything here is
fully wired and fully tested, and stays completely inert — no network calls,
no exceptions — until WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID are
set in the environment (see ``is_configured``).

Credentials (token, phone number id, API version) come from the environment,
never from the database, and are never logged or persisted anywhere — a
leaked WhatsApp token lets anyone message the business's customers. The admin
*destination* number is a low-stakes setting, not a secret, so it lives in
``core.models.StoreConfiguration`` (admin-editable, no redeploy needed); see
``core/models.py`` for that split.

Meta requires an approved message *template* for any business-initiated
message sent outside a customer's 24-hour service window. Every alert this
module sends (new order to admin, delivery offer to rider, no-rider fallback
to admin) is business-initiated, so template sending is the only send path
implemented — there is no free-text fallback to "fake" activation before the
owner has actually created and had the templates approved in Meta Business
Manager. See the setup report for the exact templates to create.
"""
import logging
import os

import requests
from django.db import transaction

logger = logging.getLogger("core.whatsapp")

REQUEST_TIMEOUT_SECONDS = 5
DEFAULT_API_VERSION = "v20.0"


def _access_token():
    return os.getenv("WHATSAPP_ACCESS_TOKEN")


def _phone_number_id():
    return os.getenv("WHATSAPP_PHONE_NUMBER_ID")


def _api_version():
    return os.getenv("WHATSAPP_API_VERSION", DEFAULT_API_VERSION)


def is_configured():
    """True once both Cloud API credentials are present in the environment.

    Everything else in this module is a no-op until this is true — that is
    the whole "ships dormant" contract.
    """
    return bool(_access_token() and _phone_number_id())


def _messages_url():
    return f"https://graph.facebook.com/{_api_version()}/{_phone_number_id()}/messages"


def send_whatsapp(to, *, kind, template_name, params, language_code="en", related_order=""):
    """Send an approved WhatsApp template message via the Meta Cloud API.

    ``params`` is an ordered list of the template's numbered body parameters
    (``{{1}}``, ``{{2}}``, ...), stringified. Returns True/False; **never
    raises** — a broken or unconfigured WhatsApp integration must never be
    able to fail the order/dispatch flow that triggered the alert.

    No-op (returns False, does nothing else) when:
      - ``to`` is blank (no destination known), or
      - the provider is unconfigured (``is_configured()`` is False).
    In both cases nothing is written to WhatsAppAlertLog — those are not
    "attempts", they're the expected dormant/unset state.

    When an attempt IS made (configured + a destination present), the
    outcome — success or failure, never the token — is always recorded in
    WhatsAppAlertLog so a silent no-send is visible from the admin.
    """
    if not to:
        logger.info("whatsapp: skipping %s alert — no destination number configured", kind)
        return False
    if not is_configured():
        logger.info("whatsapp: skipping %s alert to %s — provider not configured", kind, to)
        return False

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
            "components": [{
                "type": "body",
                "parameters": [{"type": "text", "text": str(p)} for p in params],
            }],
        },
    }

    success = False
    error = ""
    try:
        response = requests.post(
            _messages_url(),
            headers={"Authorization": f"Bearer {_access_token()}"},
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        success = response.ok
        if not success:
            error = f"HTTP {response.status_code}: {response.text[:300]}"
    except Exception as exc:  # network error, timeout, DNS failure, ... — never raise
        error = f"{type(exc).__name__}: {exc}"

    if not success:
        logger.warning("whatsapp: %s alert to %s failed: %s", kind, to, error)

    from core.models import WhatsAppAlertLog  # local import: keep module import-light

    WhatsAppAlertLog.objects.create(
        recipient=to, kind=kind, related_order=related_order,
        payload_summary=" | ".join(str(p) for p in params)[:300],
        success=success, error=error[:500],
    )
    return success


def send_whatsapp_on_commit(to, **kwargs):
    """Defer ``send_whatsapp`` to after the current DB transaction commits.

    Mirrors ``food.services.notify``'s use of ``transaction.on_commit`` for
    Expo push: callers here run inside ``@transaction.atomic`` blocks that
    sometimes hold ``select_for_update()`` row locks (order placement, the
    rider offer/accept cycle), and this is a blocking HTTP call with its own
    timeout. Running it before commit would pin a lock — or roll back an
    otherwise-successful order — on a slow or hanging WhatsApp response.
    ``on_commit`` runs the call only after the transaction commits, or
    immediately if there is no open transaction.
    """
    transaction.on_commit(lambda: send_whatsapp(to, **kwargs))
