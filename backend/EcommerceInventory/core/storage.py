"""Single implementation of the S3-or-local file storage used by
``FileUploadViewInS3`` (interactive uploads) and ``seed_store_catalog``
(image re-hosting). S3 when AWS keys are configured, else local
``MEDIA_ROOT``/``MEDIA_URL`` — exact branching that used to live inline in
the view, extracted so anything that needs to store a file (not just an
HTTP upload request) can call it directly.
"""
import os

from django.conf import settings

AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
AWS_ACESS_KEY_SECRET = settings.AWS_ACESS_KEY_SECRET
AWS_S3_REGION_NAME = settings.AWS_S3_REGION_NAME
AWS_STORAGE_BUCKET_NAME = settings.AWS_STORAGE_BUCKET_NAME
MEDIA_ROOT = settings.MEDIA_ROOT
MEDIA_URL = settings.MEDIA_URL


def use_s3():
    return (
        AWS_ACCESS_KEY_ID
        and AWS_ACESS_KEY_SECRET
        and AWS_ACCESS_KEY_ID != 'ACCESS_KEY_ID'
        and AWS_ACESS_KEY_SECRET != 'AWS_ACESS_KEY_SECRET'
    )


def save_file(filename: str, content: bytes, content_type: str) -> str:
    """Persist ``content`` under ``filename`` (already unique) and return its
    public URL — S3 when AWS keys are configured, else ``MEDIA_ROOT/uploads/``.
    """
    file_path = "uploads/" + filename

    if use_s3():
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

    upload_dir = os.path.join(MEDIA_ROOT, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    with open(os.path.join(upload_dir, filename), "wb") as destination:
        destination.write(content)
    return f"{MEDIA_URL}uploads/{filename}"
