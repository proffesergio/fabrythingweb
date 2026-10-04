"""Push sender — FCM legacy HTTP API with graceful degradation.

Needs FCM_SERVER_KEY (Firebase Console → Project settings → Cloud
Messaging). Without it every send resolves to skipped, never an exception:
the desk UI shows "not configured" and the campaign is logged as such.
"""
import logging
import os

import requests

logger = logging.getLogger(__name__)

FCM_URL = "https://fcm.googleapis.com/fcm/send"
BATCH = 500


def fcm_configured() -> bool:
    return bool(os.getenv("FCM_SERVER_KEY", "").strip())


def send_push(devices, title: str, body: str, url: str = "") -> dict:
    """Send to an iterable of PushDevice. Returns sent/failed/skipped counts
    and deactivates tokens FCM reports as permanently invalid."""
    devices = [d for d in devices if d.is_active and d.token]
    key = os.getenv("FCM_SERVER_KEY", "").strip()
    if not key:
        return {"sent": 0, "failed": 0, "skipped": len(devices),
                "note": "FCM_SERVER_KEY not set — subscribers kept, nothing sent"}
    sent = failed = 0
    dead = []
    data = {"title": title, "body": body}
    if url:
        data["url"] = url
    for i in range(0, len(devices), BATCH):
        chunk = devices[i:i + BATCH]
        try:
            r = requests.post(
                FCM_URL,
                headers={"Authorization": f"key={key}",
                         "Content-Type": "application/json"},
                json={"registration_ids": [d.token for d in chunk],
                      "notification": {"title": title, "body": body},
                      "data": data},
                timeout=15,
            )
            r.raise_for_status()
            for dev, res in zip(chunk, r.json().get("results", [])):
                if res.get("message_id"):
                    sent += 1
                else:
                    failed += 1
                    if res.get("error") in ("NotRegistered",
                                            "InvalidRegistration"):
                        dead.append(dev.pk)
        except Exception as exc:  # network/FCM outage — count, never raise
            logger.warning("FCM batch failed: %s", exc)
            failed += len(chunk)
    if dead:
        from .models import PushDevice
        PushDevice.objects.filter(pk__in=dead).update(is_active=False)
    return {"sent": sent, "failed": failed, "skipped": 0, "note": ""}
