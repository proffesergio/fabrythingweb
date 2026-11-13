"""Durable, bounded store operations; never put inference in a web request."""

import uuid
from typing import ClassVar

from django.db import models
from django.utils import timezone


class OperationsPolicy(models.Model):
    auto_clean_images = models.BooleanField(default=True)
    database_budget_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    object_budget_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    budget_note = models.CharField(max_length=200, blank=True)
    whatsapp_enabled = models.BooleanField(default=True)
    whatsapp_template = models.CharField(
        max_length=100, default="store_new_order_admin"
    )
    whatsapp_language = models.CharField(max_length=15, default="en")
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def current(cls):
        return cls.objects.get_or_create(pk=1)[0]


class ImageCleanupJob(models.Model):
    product = models.ForeignKey(
        "catalog.Products", on_delete=models.CASCADE, related_name="image_cleanup_jobs"
    )
    slot = models.PositiveSmallIntegerField(default=0)
    source_hash = models.CharField(max_length=64)
    original_url = models.TextField()
    backup_url = models.TextField(blank=True)
    output_url = models.TextField(blank=True)
    status = models.CharField(max_length=20, default="queued", db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    lease_token = models.UUIDField(default=uuid.uuid4)
    lease_until = models.DateTimeField(null=True, blank=True)
    error = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                fields=["product", "slot", "source_hash"],
                name="unique_product_image_cleanup",
            )
        ]
        indexes: ClassVar[list] = [models.Index(fields=["status", "created_at"])]


class StoredAsset(models.Model):
    """Ledger of writes since activation, not an invented historical bucket total."""

    url_hash = models.CharField(max_length=64, unique=True)
    url = models.TextField()
    backend = models.CharField(max_length=15)
    byte_size = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class CapacitySnapshot(models.Model):
    database_bytes = models.PositiveBigIntegerField(null=True)
    database_image_bytes = models.PositiveBigIntegerField(default=0)
    object_bytes = models.PositiveBigIntegerField(null=True)
    object_count = models.PositiveBigIntegerField(null=True)
    object_complete = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)


class WorkerHeartbeat(models.Model):
    name = models.CharField(max_length=30, unique=True)
    status = models.CharField(max_length=30, default="starting")
    detail = models.CharField(max_length=200, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class ImageWorkerLease(models.Model):
    token = models.UUIDField(default=uuid.uuid4)
    until = models.DateTimeField(default=timezone.now)


class OrderAlert(models.Model):
    order = models.OneToOneField(
        "orders.Order", on_delete=models.CASCADE, related_name="whatsapp_alert"
    )
    recipient = models.CharField(max_length=20)
    template = models.CharField(max_length=100)
    language = models.CharField(max_length=15, default="en")
    params = models.JSONField(default=list)
    status = models.CharField(max_length=20, default="queued", db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    available_at = models.DateTimeField(default=timezone.now)
    lease_until = models.DateTimeField(null=True, blank=True)
    lease_token = models.UUIDField(default=uuid.uuid4)
    provider_id = models.CharField(max_length=255, blank=True, db_index=True)
    error = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class WhatsAppDeliveryReceipt(models.Model):
    provider_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20)
    updated_at = models.DateTimeField(auto_now=True)
