from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.utils import timezone

AFFILIATE_CONFIG_CACHE_KEY = "affiliate_config"


class BannerQuerySet(models.QuerySet):
    def active(self, at=None):
        """Active *and* inside its scheduling window (both bounds optional).
        A banner outside its window must never be served -- see
        PublicBannerListView, which is the only caller of this in
        production code (the schedule test in test_banners.py exercises it
        directly)."""
        at = at or timezone.now()
        return (
            self.filter(is_active=True)
            .filter(models.Q(starts_at__isnull=True) | models.Q(starts_at__lte=at))
            .filter(models.Q(ends_at__isnull=True) | models.Q(ends_at__gte=at))
        )


class Banner(models.Model):
    """Homepage hero banner: a transparent PNG product cut-out composited
    over a configurable background, with a named animation preset and a CTA
    that resolves to either a catalog product or a raw URL.

    `image` reuses the same content-addressed upload path as every other
    image field in this project (`core.storage.save_file` / POST
    /api/uploads/ -> `core.models.ImageBlob`, served at
    `/api/media/<sha256>/`) rather than a new upload mechanism -- see
    core/storage.py for why a local-disk fallback would silently vanish on
    Render's ephemeral filesystem.
    """

    class AnimationStyle(models.TextChoices):
        FADE_UP = "FADE_UP", "Fade up"
        SLIDE_IN = "SLIDE_IN", "Slide in"
        FLOAT = "FLOAT", "Float / parallax"
        ZOOM = "ZOOM", "Zoom"

    image = models.CharField(
        max_length=500,
        help_text="Transparent PNG product cut-out. Upload via POST /api/uploads/ "
                  "and store the returned URL here.",
    )
    eyebrow = models.CharField(max_length=60, blank=True, default="")
    headline = models.CharField(max_length=200)
    subtext = models.CharField(max_length=300, blank=True, default="")
    animation_style = models.CharField(
        max_length=20, choices=AnimationStyle.choices, default=AnimationStyle.FADE_UP,
    )
    background = models.CharField(
        max_length=255, default="#1a1a2e",
        help_text="CSS colour or gradient for the banner background, e.g. "
                  "'#1a1a2e' or 'linear-gradient(135deg,#1a1a2e,#16213e)'.",
    )

    cta_label = models.CharField(max_length=60, blank=True, default="Shop Now")
    # A direct product link outranks cta_url when both happen to be set (see
    # BannerPublicSerializer.get_cta_link) -- the owner specifically asked
    # for "direct product linking"; the raw URL is only a fallback for a
    # banner that isn't about one specific product (e.g. a sitewide sale).
    cta_product = models.ForeignKey(
        "catalog.Products", null=True, blank=True, on_delete=models.SET_NULL, related_name="banners",
    )
    cta_url = models.CharField(max_length=500, blank=True, default="")

    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    # Optional scheduling window -- a banner with neither bound set is always
    # in-window as long as is_active is True. See BannerQuerySet.active().
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = BannerQuerySet.as_manager()

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return f"Banner #{self.pk}: {self.headline}"


class Cart(models.Model):
    """
    Server-side cart for a signed-in customer.

    Guests keep their cart in localStorage; on login/registration the client
    POSTs the local cart to the merge endpoint, which unions it into this
    persistent cart so nothing is lost across devices.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart<{self.user_id}>"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        "catalog.ProductVariant", on_delete=models.CASCADE, related_name="cart_items"
    )
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cart", "variant"], name="uq_cartitem_cart_variant")
        ]

    def __str__(self):
        return f"{self.quantity} x variant {self.variant_id}"


# ─── Affiliate automation (Rokomari and, in future, other programmes) ──────
#
# The owner is a registered Rokomari affiliate. Their dashboard only hands
# out an opaque rkmri.co/<random> short link with no way to construct one
# ourselves -- but resolving one shows it 302s to a plain parameterised URL:
#
#     https://rkmri.co/R5MEpp0p0IEI/  ->
#     https://www.rokomari.com/quick-cart?affId=Ma8A710222i0iRo&affs=70278
#         &cma=604800&productId=531074
#
# So attribution rides on ordinary query parameters, which means we can build
# a link for ANY product ourselves -- no manual per-product dashboard
# round-trip needed. This is reverse-engineered, not contracted: Rokomari can
# change the scheme (or the owner's ids) with no notice, so the params below
# are admin-editable config, never hardcoded in a view/template, and
# AffiliateProduct.manual_short_link exists as an escape hatch (paste a real
# generated link and it wins over anything constructed here). See
# storefront/services_affiliate.py for the actual link-building logic.


class AffiliateConfig(models.Model):
    """Singleton (pk=1, cached) holding the current affiliate programme's
    attribution query params -- follows the same get_solo() pattern as
    core.models.StoreConfiguration / food.models.DeliveryPricing.

    One row today because there is exactly one live programme (Rokomari).
    ``AffiliateProduct.program`` already distinguishes products by programme
    so a second config row (or a program->config lookup) is a additive change
    later, not a rewrite.
    """

    base_url = models.URLField(max_length=300, default="https://www.rokomari.com/")
    affiliate_id = models.CharField(
        max_length=64, default="Ma8A710222i0iRo",
        help_text="Rokomari's 'affId' query param -- the owner's affiliate account id.",
    )
    sub_id = models.CharField(
        max_length=32, default="70278",
        help_text="Rokomari's 'affs' query param (sub-affiliate/site id).",
    )
    cookie_window_seconds = models.PositiveIntegerField(
        default=604800,
        help_text="Rokomari's 'cma' query param -- attribution cookie lifetime in seconds "
                  "(604800 = 7 days).",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Affiliate Config"
        verbose_name_plural = "Affiliate Config"

    def __str__(self):
        return f"Affiliate config (affId={self.affiliate_id}, affs={self.sub_id})"

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce singleton
        super().save(*args, **kwargs)
        cache.delete(AFFILIATE_CONFIG_CACHE_KEY)

    @classmethod
    def get_solo(cls):
        obj = cache.get(AFFILIATE_CONFIG_CACHE_KEY)
        if obj is None:
            obj, _ = cls.objects.get_or_create(pk=1)
            cache.set(AFFILIATE_CONFIG_CACHE_KEY, obj, timeout=300)
        return obj


# Code, not an admin-editable string -- adding a programme needs a
# link-building branch written in services_affiliate.py either way, mirroring
# catalog.models.ADAPTER_CHOICES's reasoning exactly.
AFFILIATE_PROGRAM_CHOICES = [
    ("rokomari", "Rokomari.com"),
]

AFFILIATE_LINK_TYPE_CHOICES = [
    ("CART", "Cart link (quick-cart)"),
    ("PRODUCT", "Product page link"),
]


class AffiliateProductQuerySet(models.QuerySet):
    def active(self, at=None):
        """Active *and* inside its scheduling window -- same shape as
        BannerQuerySet.active() above; this is the only path that may ever
        serve a product publicly or resolve its redirect."""
        at = at or timezone.now()
        return (
            self.filter(is_active=True)
            .filter(models.Q(starts_at__isnull=True) | models.Q(starts_at__lte=at))
            .filter(models.Q(ends_at__isnull=True) | models.Q(ends_at__gte=at))
        )

    def for_sidebar(self, at=None):
        return self.active(at).filter(show_in_sidebar=True)

    def for_deals_page(self, at=None):
        return self.active(at).filter(show_on_deals_page=True)

    def for_category(self, category_slug, at=None):
        return (
            self.active(at)
            .filter(show_in_category_grid=True, grid_categories__slug=category_slug)
            .distinct()
        )


class AffiliateProduct(models.Model):
    """A product promoted via an outside affiliate programme (Rokomari
    today). ``program`` keeps the door open for a second programme without a
    schema rewrite -- see AFFILIATE_PROGRAM_CHOICES.

    The outbound link is never stored -- it is built at read/redirect time
    from AffiliateConfig + this row's remote_product_id/link_type (see
    services_affiliate.build_affiliate_link), so a config change (new affId,
    scheme change) retroactively fixes every product's link with no
    migration. ``manual_short_link`` overrides that construction entirely.

    Per-product placement is three independent booleans (the owner explicitly
    asked for "let me choose what products gets visible where"): one product
    can be sidebar-only, another can appear in the sidebar AND the deals page
    AND several category grids at once.
    """

    program = models.CharField(max_length=32, choices=AFFILIATE_PROGRAM_CHOICES, default="rokomari")
    remote_product_id = models.CharField(
        max_length=64, help_text="The product's id on the affiliate site (Rokomari's numeric productId).")
    source_url = models.URLField(
        max_length=500, help_text="The affiliate site's own product page (reference only -- no tracking params).")
    title = models.CharField(max_length=255)
    brand = models.CharField(max_length=255, blank=True, default="")
    # Re-hosted via core.storage.save_file (catalog.services_import.import_image,
    # reused here verbatim) -- never hotlink the source CDN, see core/storage.py
    # for why that silently vanishes on Render's ephemeral disk.
    image = models.CharField(max_length=500, blank=True, default="")
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    current_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    commission_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Commission earned per sale, when the programme discloses it.")
    link_type = models.CharField(
        max_length=10, choices=AFFILIATE_LINK_TYPE_CHOICES, default="CART",
        help_text="Cart (quick-buy) link or product-page link -- chosen per product.")
    manual_short_link = models.URLField(
        max_length=300, blank=True, default="",
        help_text="Optional pasted rkmri.co short link. When set, this is used INSTEAD of "
                  "the constructed link -- the owner's escape hatch if the constructed-link "
                  "scheme ever stops attributing.")

    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    display_order = models.IntegerField(default=0)
    click_count = models.PositiveIntegerField(default=0)

    show_in_sidebar = models.BooleanField(default=False, help_text="Rotating sidebar/section widget.")
    show_on_deals_page = models.BooleanField(default=False, help_text="Dedicated Deals page.")
    show_in_category_grid = models.BooleanField(
        default=False, help_text="Inject into the category-grid pages listed in grid_categories.")
    grid_categories = models.ManyToManyField(
        "catalog.Categories", blank=True, related_name="affiliate_products",
        help_text="Which of our taxonomy categories this product's grid injection appears in.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AffiliateProductQuerySet.as_manager()

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return f"[{self.program}] {self.title or self.remote_product_id}"
