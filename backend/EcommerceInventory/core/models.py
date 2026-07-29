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
    # Where WhatsApp order alerts land (core.whatsapp). This is a *number*, not
    # a credential, so it lives here rather than in an env var — the owner can
    # change it from the admin panel without a redeploy. The Cloud API token
    # and phone_number_id stay in env vars (see core/whatsapp.py); a leaked
    # destination number is not a security incident the way a leaked token is.
    # International format, digits only, no leading "+" (e.g. "8801XXXXXXXXX").
    whatsapp_admin_number = models.CharField(max_length=20, blank=True, default="")
    # Facebook Messenger deep link (m.me). Meta discontinued the embeddable
    # Customer Chat Plugin in 2024, so the storefront button just opens
    # https://m.me/<this value> in a new tab instead of an in-page widget.
    # Accepts either the numeric Page ID or the page's username — both work
    # in an m.me/ URL. Blank means "not configured yet": the storefront must
    # not render the button at all in that case (see StoreConfigView).
    messenger_page_id = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Facebook Page ID (numeric) or Page username — either works in an "
                  "m.me/ link. Leave blank to hide the Messenger button on the storefront.",
    )
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


class WhatsAppAlertLog(models.Model):
    """One row per WhatsApp Cloud API send *attempt* (core.whatsapp.send_whatsapp).

    Written only when a send was actually attempted — i.e. the provider was
    configured (env credentials present) and a destination number was known.
    A genuinely dormant/unconfigured provider never touches this table, so an
    empty table is expected until the owner pastes in credentials.

    This exists because the real failure mode of a "ships dormant" alert
    integration is not a loud crash — it's a silent no-send nobody notices.
    The admin list for this model is how the owner confirms alerts are
    actually going out once credentials are in.
    """

    recipient = models.CharField(max_length=32)
    kind = models.CharField(max_length=32)
    related_order = models.CharField(max_length=32, blank=True, default="")
    # A short, human-readable summary of the template parameters sent — never
    # the access token, which this module never receives in the first place.
    payload_summary = models.CharField(max_length=300, blank=True, default="")
    success = models.BooleanField(default=False)
    error = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["kind", "related_order"])]

    def __str__(self):
        status = "OK" if self.success else "FAILED"
        return f"[{status}] {self.kind} -> {self.recipient} ({self.related_order})"
