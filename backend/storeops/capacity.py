"""Measured usage with explicit limits/provenance. Never infer a provider quota."""

import hashlib
import logging
import time
from datetime import timedelta
from urllib.parse import urlsplit

from catalog.models import Products
from core import storage
from core.models import ImageBlob
from django.conf import settings
from django.core.cache import cache
from django.db.models import Sum
from django.utils import timezone
from nobleseek.views_operations import database_size

from .models import (
    CapacitySnapshot,
    OperationsPolicy,
    StoredAsset,
    WhatsAppDeliveryReceipt,
)


def record_asset(url, content):
    StoredAsset.objects.update_or_create(
        url_hash=hashlib.sha256(url.encode()).hexdigest(),
        defaults={
            "url": url,
            "byte_size": len(content),
            "backend": "object" if storage.use_s3() else "database",
        },
    )


def object_inventory():
    if not storage.use_s3():
        return None, None, False
    from boto3.session import Session
    from botocore.config import Config

    client = Session(
        aws_access_key_id=storage.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=storage.AWS_ACESS_KEY_SECRET,
        region_name=storage.AWS_S3_REGION_NAME or "auto",
    ).client(
        "s3",
        endpoint_url=storage.AWS_S3_ENDPOINT_URL or None,
        config=Config(connect_timeout=3, read_timeout=5, retries={"max_attempts": 0}),
    )
    total, count, token = 0, 0, None
    # Full bucket inventory up to 20k objects, once an hour in the worker.
    # Beyond this bound expose a lower bound, never a false remaining capacity.
    started = time.monotonic()
    for _ in range(20):
        if time.monotonic() - started > 30:
            break
        args = {"Bucket": storage.AWS_STORAGE_BUCKET_NAME, "MaxKeys": 1000}
        if token:
            args["ContinuationToken"] = token
        page = client.list_objects_v2(**args)
        for item in page.get("Contents", []):
            total += item["Size"]
            count += 1
        if not page.get("IsTruncated"):
            return total, count, True
        token = page.get("NextContinuationToken")
        if not token:
            break
    return total, count, False


def take_snapshot():
    latest = CapacitySnapshot.objects.order_by("-created_at").first()
    now = timezone.now()
    if latest and latest.created_at > now - timedelta(hours=1):
        return latest
    size = database_size()["size_bytes"]
    objects, count, complete = None, None, False
    try:
        objects, count, complete = object_inventory()
    except Exception as exc:  # noqa: BLE001 - snapshot records unavailable provider data
        logging.getLogger(__name__).warning(
            "Object inventory unavailable (%s).", type(exc).__name__
        )
    snap = CapacitySnapshot.objects.create(
        database_bytes=size,
        database_image_bytes=ImageBlob.objects.aggregate(n=Sum("byte_size"))["n"] or 0,
        object_bytes=objects,
        object_count=count,
        object_complete=complete,
    )
    CapacitySnapshot.objects.filter(created_at__lt=now - timedelta(days=35)).delete()
    WhatsAppDeliveryReceipt.objects.filter(
        updated_at__lt=now - timedelta(days=35)
    ).delete()
    return snap


def capacity_item(used, budget, *, complete=True, measured_at=None):
    known = used is not None and budget is not None and budget > 0 and complete
    ratio = used / budget if known else None
    return {
        "used_bytes": used,
        "budget_bytes": budget,
        "budget_source": "operator-configured" if budget else "unverified",
        "remaining_bytes": max(0, budget - used) if known else None,
        "percent": round(ratio * 100, 1) if known else None,
        "status": "critical"
        if known and ratio >= 0.9
        else "warning"
        if known and ratio >= 0.75
        else "healthy"
        if known
        else "unknown",
        "measurement_complete": complete,
        "measured_at": measured_at,
    }


def capacity_report():
    policy = OperationsPolicy.current()
    latest = CapacitySnapshot.objects.order_by("-created_at").first()
    measured = latest.created_at if latest else None
    current = cache.get("storeops_measured_database")
    if current is None:
        current = {
            "database_bytes": database_size()["size_bytes"],
            "image_bytes": ImageBlob.objects.aggregate(n=Sum("byte_size"))["n"] or 0,
            "measured_at": timezone.now(),
        }
        cache.set("storeops_measured_database", current, 60)
    db = capacity_item(
        current["database_bytes"],
        policy.database_budget_bytes,
        measured_at=current["measured_at"],
    )
    obj = capacity_item(
        latest.object_bytes if latest else None,
        policy.object_budget_bytes,
        complete=bool(latest and latest.object_complete),
        measured_at=measured,
    )
    old = (
        CapacitySnapshot.objects.filter(
            created_at__lte=timezone.now() - timedelta(hours=24)
        )
        .order_by("-created_at")
        .first()
    )
    for item, field in ((db, "database_bytes"), (obj, "object_bytes")):
        days_left = None
        if (
            latest
            and old
            and item["remaining_bytes"] is not None
            and getattr(old, field) is not None
        ):
            growth = (getattr(latest, field) or 0) - getattr(old, field)
            days = (latest.created_at - old.created_at).total_seconds() / 86400
            complete_history = field != "object_bytes" or (
                latest.object_complete and old.object_complete
            )
            if growth > 0 and days >= 1 and complete_history:
                days_left = round(item["remaining_bytes"] / (growth / days), 1)
        item["projected_days_remaining"] = days_left
    routes = {
        "database": 0,
        "object": 0,
        "external": 0,
        "products_sampled": 0,
        "complete": True,
    }
    base = storage.AWS_S3_PUBLIC_BASE_URL
    object_host = (
        urlsplit(base).hostname
        if base
        else (
            storage.AWS_STORAGE_BUCKET_NAME + ".s3.amazonaws.com"
            if storage.AWS_STORAGE_BUCKET_NAME
            else None
        )
    )
    from .images import image_url

    owned_media_hosts = {
        "www.fabrything.com",
        "fabrything.com",
        "fabrythingapi.vercel.app",
    } | (set(settings.ALLOWED_HOSTS) - {"*"})
    for images in (
        Products.objects.order_by("pk")
        .values_list("image", flat=True)
        .iterator(chunk_size=250)
    ):
        if routes["products_sampled"] >= 10000:
            routes["complete"] = False
            break
        routes["products_sampled"] += 1
        for item in (images or [])[:12]:
            url = image_url(item)
            if not url:
                continue
            parsed = urlsplit(url)
            if parsed.path.startswith("/api/media/") and (
                not parsed.netloc or parsed.hostname in owned_media_hosts
            ):
                routes["database"] += 1
            elif object_host and parsed.hostname == object_host:
                routes["object"] += 1
            else:
                routes["external"] += 1
    return {
        "database": db,
        "object_storage": obj,
        "database_image_bytes": current["image_bytes"],
        "database_image_count": ImageBlob.objects.count(),
        "object_count": latest.object_count if latest else None,
        "storage_backend": "object" if storage.use_s3() else "database",
        "object_provider": "Cloudflare R2"
        if "r2.cloudflarestorage.com" in (storage.AWS_S3_ENDPOINT_URL or "")
        else "S3-compatible"
        if storage.use_s3()
        else None,
        "tracked_object_bytes": StoredAsset.objects.filter(backend="object").aggregate(
            n=Sum("byte_size")
        )["n"]
        or 0,
        "image_locations": routes,
        "stale": not latest or latest.created_at < timezone.now() - timedelta(hours=2),
        "recommendation": "Move database image payloads to object storage before adding databases. Upgrade the primary plan or design a reviewed data partition; a second connection does not add capacity automatically.",
        "quota_note": "Budgets are operator-entered limits, not provider-verified quotas. R2 free storage allowance is not a hard bucket limit. Bucket inventory includes all object versions only when supported by the provider; this view counts current objects.",
    }


def ensure_write_capacity(extra_bytes):
    policy = OperationsPolicy.current()
    if storage.use_s3():
        if policy.object_budget_bytes:
            latest = CapacitySnapshot.objects.order_by("-created_at").first()
            if (
                not latest
                or not latest.object_complete
                or latest.object_bytes is None
                or latest.created_at < timezone.now() - timedelta(hours=2)
            ):
                raise RuntimeError("Capacity measurement needs refresh.")
            if latest.object_bytes + extra_bytes >= policy.object_budget_bytes * 0.95:
                raise RuntimeError("Object storage budget headroom is too low.")
    elif policy.database_budget_bytes:
        measured = database_size()["size_bytes"]
        if (
            measured is None
            or measured + extra_bytes >= policy.database_budget_bytes * 0.95
        ):
            raise RuntimeError("Database budget headroom is too low.")
