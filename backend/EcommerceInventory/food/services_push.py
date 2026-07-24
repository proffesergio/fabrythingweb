"""Expo push send path — stdlib only (no new dependency).

`notify()` in food/services.py calls `send_expo_push` after creating each
in-app Notification, so a push failure never blocks or breaks the request
that triggered it: `_post_to_expo` swallows any network/HTTP error and
returns an empty receipt list on failure.
"""
import json
import urllib.request

from food.models import DeviceToken

EXPO_URL = "https://exp.host/--/api/v2/push/send"
_CHUNK = 100


def _post_to_expo(messages):
    """POST a batch of Expo message dicts; return the list of per-message receipts.

    Network/HTTP errors are swallowed (best-effort delivery) and reported as an
    empty receipt list so a push failure never breaks the request that triggered it.
    """
    payload = json.dumps(messages).encode("utf-8")
    req = urllib.request.Request(
        EXPO_URL, data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body.get("data", [])
    except Exception:
        return []


def send_expo_push(tokens, title, body, data=None):
    tokens = [t for t in tokens if t]
    for i in range(0, len(tokens), _CHUNK):
        batch = tokens[i:i + _CHUNK]
        messages = [{"to": t, "title": title, "body": body, "data": data or {},
                     "sound": "default"} for t in batch]
        receipts = _post_to_expo(messages)
        for token, receipt in zip(batch, receipts):
            details = (receipt or {}).get("details") or {}
            if details.get("error") == "DeviceNotRegistered":
                DeviceToken.objects.filter(expo_token=token).update(enabled=False)
