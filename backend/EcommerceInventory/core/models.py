from decimal import Decimal

from django.core.cache import cache
from django.core.validators import MaxValueValidator, MinValueValidator
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
    # Customer-facing WhatsApp *chat* link (the floating button on the
    # storefront and food frontend) -- not to be confused with
    # `whatsapp_admin_number` above, which is where server-side order alerts
    # are sent (core/whatsapp.py). International format, digits only, no
    # leading "+" (e.g. "8801842168117"), matching the wa.me/<number> link
    # format. Blank means "not configured yet": both frontends must not
    # render the button at all in that case, same rule as messenger_page_id.
    whatsapp_chat_number = models.CharField(
        max_length=20, blank=True, default="",
        help_text="WhatsApp number for the floating chat button (digits only, no '+', "
                  "e.g. 8801842168117 -- used as wa.me/<this value>). Leave blank to "
                  "hide the button on the storefront and food frontend.",
    )
    # Platform-revenue markup on product prices -- see catalog/pricing.py for
    # the rule (max(markup_floor, base_price * markup_percentage%), the same
    # shape as food.pricing.commission_for). Admin-editable here rather than
    # an env var so the owner can retune it without a redeploy, same reason
    # DeliveryPricing lives in the database instead of settings.
    #
    # Defaults: floor=50, percentage=3%. The owner asked for "at least 50-100
    # BDT" of margin on cheap items; at 3% the catalog's median ~3,200 BDT
    # product earns ~96 BDT while the 50 BDT floor protects the ~99 BDT items
    # a flat percentage would otherwise barely touch.
    markup_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("3.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        help_text="Percentage markup applied to a product's base_price. Clamped to "
                  "0-100 on save -- a mis-typed 500% would otherwise 6x every price.",
    )
    markup_floor = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("50.00"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Minimum taka markup applied to every product regardless of price, "
                  "so a cheap item still carries a guaranteed minimum margin.",
    )
    # Master switch for selling `requires_prescription` medicines
    # (catalog.models.Products.requires_prescription). Default False because
    # the owner does not yet hold a DGDA licence -- orders.services.
    # place_cod_order refuses to sell an Rx product while this is off, so
    # flipping this one admin-editable field (no deploy) is what turns
    # medicine sales on once the licence arrives.
    rx_sales_enabled = models.BooleanField(
        default=False,
        help_text="Allow checkout of prescription-required medicines. Leave off until "
                  "a DGDA licence is in hand -- every requires_prescription product is "
                  "blocked at checkout while this is False, regardless of any other setting.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Store Configuration"
        verbose_name_plural = "Store Configuration"

    def __str__(self):
        return f"{self.store_name} config ({self.fixed_shipping_rate} {self.currency} shipping)"

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce singleton
        # Belt-and-braces clamp on top of the field validators above: the
        # validators only fire when a caller goes through full_clean() (e.g.
        # the admin form). Any other write path -- a script, a migration, a
        # test -- still must not be able to silently 6x every price on the
        # site with a mistyped percentage, so clamp unconditionally here too.
        if self.markup_percentage is not None:
            self.markup_percentage = max(Decimal("0"), min(Decimal("100"), Decimal(str(self.markup_percentage))))
        if self.markup_floor is not None:
            self.markup_floor = max(Decimal("0"), Decimal(str(self.markup_floor)))
        super().save(*args, **kwargs)
        cache.delete(CACHE_KEY)

    @classmethod
    def get_solo(cls):
        obj = cache.get(CACHE_KEY)
        if obj is None:
            obj, _ = cls.objects.get_or_create(pk=1)
            cache.set(CACHE_KEY, obj, timeout=300)
        return obj

    def shipping_for(self, subtotal, product_shipping_fees=None, free_shipping_flags=None) -> Decimal:
        """Resolve the shipping charge for a given order subtotal.

        ``product_shipping_fees`` is an optional iterable with one entry per
        cart line (Decimal/float/None) -- ``catalog.models.Products.shipping_fee``
        for the line's product. ``free_shipping_flags`` is an optional,
        parallel iterable of booleans -- ``catalog.models.Products.free_shipping``
        for the same line, marking it as an explicit free-shipping promo item
        (distinct from ``shipping_fee == 0``, which is still just a candidate
        in the max() below and only rarely wins). This is the single place
        the per-product shipping rule is implemented; do not duplicate it in
        a view.

        Rule, in order:
        1. Free-shipping-threshold, when the subtotal qualifies, wins over
           everything below and returns 0 immediately.
        2. If every cart line is a ``free_shipping`` promo item, shipping is 0.
        3. Otherwise shipping = max(fixed_shipping_rate, every non-null
           per-product fee among the *non-promo* lines) -- it's one delivery
           trip, so the bulkiest/costliest non-promo item sets the price, the
           flat rate is always the floor, and promo lines are excluded from
           the max() entirely: a free-shipping shirt must not make an
           expensive item ship free, and must not undercut the flat rate
           either. See the worked examples in docs/SHIPPING_FEES.md.
        """
        subtotal = Decimal(str(subtotal))
        if self.free_shipping_threshold is not None and subtotal >= self.free_shipping_threshold:
            return Decimal("0.00")

        product_shipping_fees = list(product_shipping_fees or [])
        free_shipping_flags = list(free_shipping_flags or [])
        if len(free_shipping_flags) < len(product_shipping_fees):
            free_shipping_flags += [False] * (len(product_shipping_fees) - len(free_shipping_flags))

        if product_shipping_fees and all(free_shipping_flags):
            return Decimal("0.00")

        candidates = [self.fixed_shipping_rate]
        for fee, is_promo in zip(product_shipping_fees, free_shipping_flags):
            if is_promo:
                continue
            if fee is not None:
                candidates.append(Decimal(str(fee)))
        return max(candidates)


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
