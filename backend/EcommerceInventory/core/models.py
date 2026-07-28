from decimal import Decimal

from django.core.cache import cache
from django.db import models

CACHE_KEY = "store_config"


class StoreConfiguration(models.Model):
    """
    Global, single-row store configuration.

    Holds the fixed COD shipping rate that is applied dynamically at order
    creation, plus store-wide toggles. Always stored at pk=1 (singleton) and
    read through ``get_solo()`` which caches the row.
    """

    fixed_shipping_rate = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("60.00"),
        help_text="Flat shipping charge applied to every order.",
    )
    free_shipping_threshold = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Optional: orders with subtotal >= this ship free. "
                  "Leave blank to always charge the fixed rate.",
    )
    cod_enabled = models.BooleanField(default=True)
    currency = models.CharField(max_length=3, default="BDT")
    store_name = models.CharField(max_length=120, default="Fabrything")
    support_phone = models.CharField(max_length=20, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Store Configuration"
        verbose_name_plural = "Store Configuration"

    def __str__(self):
        return f"{self.store_name} config ({self.fixed_shipping_rate} {self.currency} shipping)"

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce singleton
        super().save(*args, **kwargs)
        cache.delete(CACHE_KEY)

    @classmethod
    def get_solo(cls):
        obj = cache.get(CACHE_KEY)
        if obj is None:
            obj, _ = cls.objects.get_or_create(pk=1)
            cache.set(CACHE_KEY, obj, timeout=300)
        return obj

    def shipping_for(self, subtotal) -> Decimal:
        """Resolve the shipping charge for a given order subtotal."""
        subtotal = Decimal(str(subtotal))
        if self.free_shipping_threshold is not None and subtotal >= self.free_shipping_threshold:
            return Decimal("0.00")
        return self.fixed_shipping_rate


class ImageBlob(models.Model):
    """A content-addressed image, stored in the database instead of on disk.

    Render's filesystem is ephemeral and wiped on every deploy, and no S3
    keys are configured, so ``core.storage.save_file`` falls back to writing
    the bytes here rather than under ``MEDIA_ROOT``. ``sha256`` is the
    content address: the same bytes stored twice (e.g. re-running the
    catalog seeder) must resolve to the same row via ``get_or_create``,
    never a duplicate, and the hash also doubles as the public serving URL
    and the ETag (see ``core.views`` media-serving view).
    """

    sha256 = models.CharField(max_length=64, unique=True, db_index=True)
    content_type = models.CharField(max_length=100)
    data = models.BinaryField()
    byte_size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sha256} ({self.content_type}, {self.byte_size} bytes)"
