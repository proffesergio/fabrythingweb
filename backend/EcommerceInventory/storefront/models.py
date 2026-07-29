from django.conf import settings
from django.db import models
from django.utils import timezone


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
