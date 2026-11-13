"""Single-image CPU pipeline with bounded input, retained originals and CAS writes."""

import hashlib
import io
import re
import threading
import uuid
from datetime import timedelta
from urllib.parse import urlsplit

from catalog.models import Products
from core.models import ImageBlob
from core.storage import save_file
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from PIL import Image, ImageOps

from .models import ImageCleanupJob, ImageWorkerLease

MAX_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 20_000_000
_session = None
_lock = threading.Lock()


class ReviewRequired(Exception):
    pass


def image_url(item):
    return (
        item
        if isinstance(item, str)
        else item.get("url", "")
        if isinstance(item, dict)
        else ""
    )


def enqueue_product(product):
    jobs = []
    for slot, item in enumerate((product.image or [])[:12]):
        url = image_url(item)
        if not url or len(url) > 4096:
            continue
        # Do not recursively process our own normalized output.
        if ImageCleanupJob.objects.filter(product=product, output_url=url).exists():
            continue
        digest = hashlib.sha256(("u2netp-white-v1:" + url).encode()).hexdigest()
        job, _ = ImageCleanupJob.objects.get_or_create(
            product=product,
            slot=slot,
            source_hash=digest,
            defaults={"original_url": url},
        )
        jobs.append(job)
    return jobs


def read_source(url):
    parsed = urlsplit(url)
    match = re.fullmatch(r"/api/media/([a-f0-9]{64})/", parsed.path)
    # Relative DB media is safe; an arbitrary remote host with this path is not local media.
    allowed_hosts = set(getattr(settings, "ALLOWED_HOSTS", [])) - {"*"}
    if match and (not parsed.netloc or parsed.hostname in allowed_hosts):
        row = ImageBlob.objects.only("data", "byte_size").get(sha256=match[1])
        if row.byte_size > MAX_BYTES:
            raise ReviewRequired("Source exceeds the 5 MiB image limit.")
        return bytes(row.data)
    from catalog.supplier_security import supplier_get_bytes

    return supplier_get_bytes(url, max_bytes=MAX_BYTES)


def remove_background(image):
    global _session
    # Keep optional CPU libraries out of serverless web deployment dependencies.
    import onnxruntime as ort
    from rembg import new_session, remove

    if _session is None:
        # rembg's session factory uses OMP_NUM_THREADS for both ONNX thread counts.
        import os

        os.environ["OMP_NUM_THREADS"] = "1"
        _session = new_session("u2netp", providers=["CPUExecutionProvider"])
        if "CPUExecutionProvider" not in ort.get_available_providers():
            raise RuntimeError("CPU image processor is unavailable.")
    return remove(image, session=_session).convert("RGBA")


def normalize_image(content, remover=None):
    if len(content) > MAX_BYTES:
        raise ReviewRequired("Source exceeds the 5 MiB image limit.")
    with Image.open(io.BytesIO(content)) as source:
        if (
            source.width * source.height > MAX_PIXELS
            or getattr(source, "n_frames", 1) != 1
        ):
            raise ReviewRequired("Use a single image smaller than 20 megapixels.")
        image = ImageOps.exif_transpose(source).convert("RGB")
        image.thumbnail((1200, 1200))
    cutout = (remover or remove_background)(image).convert("RGBA")
    if cutout.size != image.size:
        raise ReviewRequired("Cutout dimensions changed unexpectedly.")
    alpha = cutout.getchannel("A")
    histogram = alpha.histogram()
    area = cutout.width * cutout.height
    visible = sum(histogram[40:]) / area
    removed = sum(histogram[:40]) / area
    if visible < 0.04 or removed < 0.02 or visible > 0.98:
        raise ReviewRequired("Uncertain foreground mask; review the original photo.")
    bbox = alpha.point(lambda value: 255 if value > 40 else 0).getbbox()
    subject = cutout.crop(bbox)
    subject.thumbnail((1080, 1080), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (1200, 1200), "white")
    canvas.paste(
        subject, ((1200 - subject.width) // 2, (1200 - subject.height) // 2), subject
    )
    output = io.BytesIO()
    canvas.save(output, "WEBP", quality=88, method=4)
    return output.getvalue()


def _replace_locked(job, expected, replacement):
    product = Products.objects.select_for_update().get(pk=job.product_id)
    images = list(product.image or [])
    if job.slot >= len(images) or image_url(images[job.slot]) != expected:
        return False
    current = images[job.slot]
    images[job.slot] = (
        {**current, "url": replacement} if isinstance(current, dict) else replacement
    )
    Products.objects.filter(pk=product.pk).update(
        image=images, updated_at=timezone.now()
    )
    return True


@transaction.atomic
def restore_job(pk):
    job = ImageCleanupJob.objects.select_for_update().get(pk=pk)
    if job.status != "completed" or not _replace_locked(
        job, job.output_url, job.backup_url or job.original_url
    ):
        raise ValueError("This photo changed or has no completed cleanup to restore.")
    job.status = "restored"
    job.save(update_fields=["status", "updated_at"])
    return job


@transaction.atomic
def claim_image():
    now = timezone.now()
    ImageWorkerLease.objects.get_or_create(pk=1, defaults={"until": now})
    lease = ImageWorkerLease.objects.select_for_update().get(pk=1)
    if lease.until > now:
        return None
    # A CPU worker that vanished can retry; deterministic storage keys make retries safe.
    query = ImageCleanupJob.objects.filter(
        Q(status="queued") | Q(status="processing", lease_until__lt=now), attempts__lt=3
    )
    from django.db import connection

    query = (
        query.select_for_update(skip_locked=True)
        if connection.features.has_select_for_update_skip_locked
        else query.select_for_update()
    )
    job = query.order_by("created_at").first()
    if not job:
        ImageCleanupJob.objects.filter(
            status="processing", lease_until__lt=now, attempts__gte=3
        ).update(status="failed", error="Worker lease expired; inspect before retry.")
        return None
    job.status, job.lease_token, job.lease_until = (
        "processing",
        uuid.uuid4(),
        now + timedelta(minutes=10),
    )
    job.attempts += 1
    job.save()
    lease.token, lease.until = job.lease_token, job.lease_until
    lease.save()
    return job


def process_one_image():
    # Local guard also prevents accidental parallel calls within this process.
    if not _lock.acquire(blocking=False):
        return False
    try:
        job = claim_image()
        if not job:
            return False
        try:
            content = read_source(job.original_url)
            output = normalize_image(content)
            from .capacity import ensure_write_capacity

            ensure_write_capacity(len(content) + len(output))
            digest = hashlib.sha256(content).hexdigest()
            backup = save_file(
                "original-" + digest,
                content,
                Image.MIME.get(
                    Image.open(io.BytesIO(content)).format, "application/octet-stream"
                ),
            )
            digest = hashlib.sha256(output).hexdigest()
            url = save_file("clean-" + digest + ".webp", output, "image/webp")
            with transaction.atomic():
                current = ImageCleanupJob.objects.select_for_update().get(pk=job.pk)
                if (
                    current.status != "processing"
                    or current.lease_token != job.lease_token
                ):
                    return True
                current.backup_url, current.output_url = backup, url
                current.status = (
                    "completed"
                    if _replace_locked(current, current.original_url, url)
                    else "stale"
                )
                current.error = (
                    ""
                    if current.status == "completed"
                    else "Photo changed while cleanup was running; no overwrite performed."
                )
                current.save()
        except Exception as exc:  # noqa: BLE001 - durable job boundary must record failures
            status = "review" if isinstance(exc, ReviewRequired) else "failed"
            # Never persist URLs, provider credentials or raw exception text.
            error = (
                str(exc)
                if isinstance(exc, ReviewRequired)
                else "Cleanup failed ("
                + type(exc).__name__
                + "). Check worker configuration."
            )
            ImageCleanupJob.objects.filter(
                pk=job.pk, status="processing", lease_token=job.lease_token
            ).update(status=status, error=error, updated_at=timezone.now())
        return True
    finally:
        if "job" in locals() and job:
            ImageWorkerLease.objects.filter(pk=1, token=job.lease_token).update(
                until=timezone.now()
            )
        _lock.release()
