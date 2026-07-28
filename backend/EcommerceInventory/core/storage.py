"""Single implementation of the S3-or-database file storage used by
``FileUploadViewInS3`` (interactive uploads) and ``seed_store_catalog``
(image re-hosting). S3 when AWS keys are configured; otherwise the bytes are
stored as a content-addressed row in the database (``core.models.ImageBlob``)
and served back by ``core.views.serve_media_blob`` at ``/api/media/<sha256>/``.

There deliberately is no local-disk fallback. Render's filesystem is
ephemeral and wiped on every deploy, so a local write silently disappears on
the next release — that used to be the fallback and was a live latent bug
(every admin upload and the whole product-image seed vanished on deploy).
The DB fallback is what actually survives.
"""
import hashlib

from django.conf import settings

AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
AWS_ACESS_KEY_SECRET = settings.AWS_ACESS_KEY_SECRET
AWS_S3_REGION_NAME = settings.AWS_S3_REGION_NAME
AWS_STORAGE_BUCKET_NAME = settings.AWS_STORAGE_BUCKET_NAME


def use_s3():
    return (
        AWS_ACCESS_KEY_ID
        and AWS_ACESS_KEY_SECRET
        and AWS_ACCESS_KEY_ID != 'ACCESS_KEY_ID'
        and AWS_ACESS_KEY_SECRET != 'AWS_ACESS_KEY_SECRET'
    )


def save_file(filename: str, content: bytes, content_type: str) -> str:
    """Persist ``content`` (``filename`` only matters for the S3 key — the
    database fallback is addressed by content hash, not name) and return its
    public URL — S3 when AWS keys are configured, else the DB-backed
    ``/api/media/<sha256>/`` serving URL.
    """
    if use_s3():
        file_path = "uploads/" + filename
        from boto3.session import Session

        s3_client = Session(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_ACESS_KEY_SECRET,
            region_name=AWS_S3_REGION_NAME,
        ).client("s3")
        s3_client.put_object(
            Bucket=AWS_STORAGE_BUCKET_NAME,
            Key=file_path,
            Body=content,
            ContentType=content_type,
        )
        return f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{file_path}"

    return _save_to_database(content, content_type)


def _save_to_database(content: bytes, content_type: str) -> str:
    """Content-addressed fallback: hash the bytes, reuse the row if that hash
    already exists (dedup — re-running the seeder must not duplicate blobs),
    and return the serving URL. Imported lazily so this module can still be
    imported before the app registry is ready (mirrors the existing lazy
    ``boto3`` import above).
    """
    from core.models import ImageBlob

    digest = hashlib.sha256(content).hexdigest()
    ImageBlob.objects.get_or_create(
        sha256=digest,
        defaults={
            "content_type": content_type,
            "data": content,
            "byte_size": len(content),
        },
    )
    return f"/api/media/{digest}/"
