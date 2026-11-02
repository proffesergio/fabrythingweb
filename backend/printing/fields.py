"""Shared serializer fields for the printing app.

``MediaURLField`` exists because ``core.storage.save_file`` returns a
site-relative ``/api/media/<sha256>/`` URL whenever S3/R2 keys are not
configured (i.e. the live server's DB-blob fallback). DRF's ``URLField``
rejects relative URLs, which turned every two-step upload (upload file ->
paste URL -> save) into a 400 "Enter a valid URL." — first seen on the
design-showcase thumbnail flow. This field accepts absolute http(s) URLs
and site-relative ``/...`` paths, and nothing else.
"""
from urllib.parse import urlparse

from rest_framework import serializers


class MediaURLField(serializers.CharField):
    default_error_messages = {
        "invalid": "Enter a valid URL.",
        "blank": "This field may not be blank.",
    }

    def __init__(self, **kwargs):
        kwargs.setdefault("max_length", 500)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        if value in ("", None):
            return value
        parsed = urlparse(value)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            return value
        if isinstance(value, str) and value.startswith("/") and " " not in value:
            return value
        self.fail("invalid")
