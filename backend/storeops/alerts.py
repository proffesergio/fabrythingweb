"""Durable order alerts: one outbox row per order, no blind timeout retry."""

import uuid
from datetime import timedelta

import requests
from core import whatsapp
from core.models import StoreConfiguration, WhatsAppAlertLog
from django.db import connection, transaction
from django.utils import timezone

from .models import OperationsPolicy, OrderAlert, WhatsAppDeliveryReceipt

STATUS_RANK = {"accepted": 0, "sent": 1, "failed": 2, "delivered": 3, "read": 4}


@transaction.atomic
def record_delivery(provider_id, status):
    receipt, _ = WhatsAppDeliveryReceipt.objects.get_or_create(
        provider_id=provider_id, defaults={"status": status}
    )
    receipt = WhatsAppDeliveryReceipt.objects.select_for_update().get(pk=receipt.pk)
    if STATUS_RANK.get(status, -1) > STATUS_RANK.get(receipt.status, -1):
        receipt.status = status
        receipt.save()
    rows = OrderAlert.objects.filter(provider_id=provider_id)
    for alert in rows.select_for_update():
        if STATUS_RANK.get(receipt.status, -1) > STATUS_RANK.get(alert.status, -1):
            alert.status = receipt.status
            alert.save(update_fields=["status", "updated_at"])


def enqueue_order_alert(order, params):
    policy = OperationsPolicy.current()
    number = StoreConfiguration.get_solo().whatsapp_admin_number.strip()
    if not policy.whatsapp_enabled or not number:
        return None
    return OrderAlert.objects.get_or_create(
        order=order,
        defaults={
            "recipient": number,
            "template": policy.whatsapp_template,
            "language": policy.whatsapp_language,
            "params": params,
        },
    )[0]


@transaction.atomic
def claim_alert():
    now = timezone.now()
    # A vanished worker may have submitted the message: never resend automatically.
    OrderAlert.objects.filter(status="sending", lease_until__lt=now).update(
        status="unknown",
        error="Worker stopped before confirmation. Reconcile with Meta before any resend.",
    )
    OrderAlert.objects.filter(
        status="queued", created_at__lt=now - timedelta(hours=24)
    ).update(
        status="expired",
        error="Order alert is older than 24 hours; review the order in admin.",
    )
    if not whatsapp.is_configured() or not OperationsPolicy.current().whatsapp_enabled:
        return None
    query = OrderAlert.objects.filter(
        status="queued", available_at__lte=now, attempts__lt=3
    )
    query = (
        query.select_for_update(skip_locked=True)
        if connection.features.has_select_for_update_skip_locked
        else query.select_for_update()
    )
    job = query.order_by("created_at").first()
    if not job:
        return None
    # Old order alerts are visible for review instead of surprising an admin days later.
    if job.created_at < now - timedelta(hours=24):
        job.status, job.error = (
            "expired",
            "Order alert is older than 24 hours; review the order in admin.",
        )
        job.save()
        return None
    job.status, job.lease_token = "sending", uuid.uuid4()
    job.lease_until = now + timedelta(minutes=2)
    job.attempts += 1
    job.save()
    return job


def process_one_alert():
    job = claim_alert()
    if not job:
        return False
    status, error, provider_id = "unknown", "", ""
    try:
        payload = {
            "messaging_product": "whatsapp",
            "to": job.recipient,
            "type": "template",
            "template": {
                "name": job.template,
                "language": {"code": job.language},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": str(p)} for p in job.params
                        ],
                    }
                ],
            },
        }
        response = requests.post(
            whatsapp._messages_url(),
            json=payload,
            headers={"Authorization": "Bearer " + whatsapp._access_token()},
            timeout=whatsapp.REQUEST_TIMEOUT_SECONDS,
        )
        if response.ok:
            data = response.json()
            provider_id = str(data.get("messages", [{}])[0].get("id", ""))[:255]
            status = "accepted" if provider_id else "unknown"
            error = (
                ""
                if provider_id
                else "Provider accepted the request without a message ID. Reconcile before resending."
            )
        elif response.status_code == 429:
            status = "queued" if job.attempts < 3 else "failed"
            error = "Provider rate limit; retry is bounded to three attempts."
        else:
            # Raw response text may contain credentials/PII; persist only HTTP status.
            status, error = (
                "failed",
                "Provider rejected request: HTTP " + str(response.status_code),
            )
    except Exception as exc:  # noqa: BLE001 - durable job boundary must record failures
        error = (
            "Unconfirmed request ("
            + type(exc).__name__
            + "). Check Meta before resending."
        )
    with transaction.atomic():
        current = OrderAlert.objects.select_for_update().get(pk=job.pk)
        if current.status != "sending" or current.lease_token != job.lease_token:
            return True
        current.status, current.error, current.provider_id = status, error, provider_id
        if provider_id:
            # A signed status callback can arrive before the send response commits.
            receipt = WhatsAppDeliveryReceipt.objects.filter(
                provider_id=provider_id
            ).first()
            if receipt and STATUS_RANK.get(receipt.status, -1) > STATUS_RANK.get(
                status, -1
            ):
                current.status = receipt.status
        current.available_at = timezone.now() + timedelta(minutes=5 * job.attempts)
        current.save()
        WhatsAppAlertLog.objects.create(
            recipient=job.recipient,
            kind="store_order_admin",
            related_order=current.order.order_number,
            success=status == "accepted",
            payload_summary="New-order template alert",
            error=error,
        )
    return True
