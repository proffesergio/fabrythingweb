"""Custom print-on-demand (SP6).

This is NOT an upload-and-print tool. The owner usually draws the artwork
himself from the customer's brief (typography, team name, player names +
numbers); a customer-supplied final-art image is the secondary path. The
model is built around a design-request + proof-approval loop:

    customer submits brief (+ optional reference image)
        -> owner produces artwork, attaches a proof
        -> customer approves OR requests a revision (loop back to design)
        -> approved -> production stages -> done

``PrintRequest.ALLOWED_TRANSITIONS`` + ``transition_to()`` is the single
choke point for status changes, mirroring ``food.models.FoodOrder`` -- every
view (customer decision, staff proof/status actions) routes through it so a
status write can never happen anywhere else.
"""
from decimal import Decimal

from django.conf import settings
from django.db import models

from catalog.models import SIZE_CHOICES, Products
from food.models import TimeStamped


def default_quantity_tiers():
    """Sane out-of-the-box bulk discount ladder -- admin-editable from the
    pricing config without a deploy. min_qty is inclusive; the highest tier
    whose min_qty <= the order quantity wins."""
    return [
        {"min_qty": 1, "discount_percent": 0},
        {"min_qty": 10, "discount_percent": 5},
        {"min_qty": 25, "discount_percent": 10},
        {"min_qty": 50, "discount_percent": 15},
    ]


class PrintPricingConfig(models.Model):
    """Singleton row (``get_solo()``, mirrors ``food.models.DeliveryPricing``)
    holding the one tunable that isn't already a per-area/per-garment price:
    the quantity-tier discount ladder. Garment price lives on
    ``PrintablePreset.base_price``; per-location price lives on
    ``PrintArea.price``. Nothing reads this at approval time -- the agreed
    price is snapshotted onto the ``PrintRequest`` the moment it is approved
    (see ``PrintRequest.transition_to``), so retuning a rate here never moves
    an already-approved order's books.
    """

    quantity_tiers = models.JSONField(
        default=default_quantity_tiers, blank=True,
        help_text='List of {"min_qty": int, "discount_percent": number}, '
                  "ascending by min_qty. The highest tier at or below the "
                  "order quantity applies.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_solo(cls):
        obj = cls.objects.order_by("id").first()
        return obj or cls.objects.create()

    def discount_percent_for(self, quantity):
        best = Decimal("0")
        for tier in sorted(self.quantity_tiers or [], key=lambda t: t.get("min_qty", 0)):
            if quantity >= tier.get("min_qty", 0):
                best = Decimal(str(tier.get("discount_percent", 0)))
        return best

    def __str__(self):
        return "Print pricing config"


class PrintArea(TimeStamped):
    """A print location the owner offers (front/back/sleeve/collar/...),
    each with its own flat per-print charge. A plain admin-editable lookup
    table rather than a fixed enum, so a new location doesn't need a
    deploy -- "the owner must control ... which print locations exist ...
    with a price per location" (SP6 spec)."""

    name = models.CharField(max_length=50, unique=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return f"{self.name} (+{self.price})"


class PrintablePreset(TimeStamped):
    """A garment configuration the owner has opted into custom printing,
    e.g. "Round Neck T-Shirt" or "Football Jersey" -- controls which
    garments are printable at all, and their base (blank garment) price.

    ``product`` is optional: the owner can list a printable garment before
    (or without) a full catalog listing exists for it. When it does point at
    a real ``catalog.Products`` row, that row is what ``PrintRequest.product``
    gets set to on submission (see ``printing.services.create_print_request``).
    """

    product = models.OneToOneField(
        Products, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="printable_preset",
    )
    name = models.CharField(max_length=150)
    base_price = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    available_colors = models.JSONField(default=list, blank=True)
    available_sizes = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name


class PrintRequest(TimeStamped):
    """A customer's custom-print job: the brief, the garment, the
    proof-approval loop's current stage, and the agreed price once it's
    locked in."""

    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        IN_DESIGN = "IN_DESIGN", "In Design"
        PROOF_READY = "PROOF_READY", "Proof Ready"
        REVISION_REQUESTED = "REVISION_REQUESTED", "Revision Requested"
        APPROVED = "APPROVED", "Approved"
        IN_PRODUCTION = "IN_PRODUCTION", "In Production"
        READY = "READY", "Ready"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    # Forward-only loop, mirroring food.models.FoodOrder.ALLOWED_TRANSITIONS.
    # PROOF_READY <-> the (REVISION_REQUESTED -> IN_DESIGN) pair is the only
    # cycle; everything else only moves forward or to CANCELLED.
    ALLOWED_TRANSITIONS = {
        Status.SUBMITTED: {Status.IN_DESIGN, Status.CANCELLED},
        Status.IN_DESIGN: {Status.PROOF_READY, Status.CANCELLED},
        Status.PROOF_READY: {Status.REVISION_REQUESTED, Status.APPROVED, Status.CANCELLED},
        Status.REVISION_REQUESTED: {Status.IN_DESIGN, Status.CANCELLED},
        Status.APPROVED: {Status.IN_PRODUCTION, Status.CANCELLED},
        Status.IN_PRODUCTION: {Status.READY, Status.CANCELLED},
        Status.READY: {Status.COMPLETED, Status.CANCELLED},
        Status.COMPLETED: set(),
        Status.CANCELLED: set(),
    }

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="print_requests",
    )
    # The blank tee/jersey being printed. Nullable: a brief can arrive before
    # a specific catalog garment is pinned down, and some jobs (an owner-only
    # promo run) never have one.
    product = models.ForeignKey(
        Products, on_delete=models.SET_NULL, null=True, blank=True, related_name="print_requests",
    )
    preset = models.ForeignKey(
        PrintablePreset, on_delete=models.SET_NULL, null=True, blank=True, related_name="print_requests",
    )
    print_areas = models.ManyToManyField(PrintArea, blank=True, related_name="print_requests")

    color = models.CharField(max_length=50, blank=True, default="")
    size = models.CharField(max_length=10, choices=SIZE_CHOICES, blank=True, default="")
    quantity = models.PositiveIntegerField(default=1)
    brief = models.TextField()
    # JSONField list of /api/media/<sha>/ (or S3) URLs -- same convention as
    # catalog.Products.image. Populated via PrintReferenceImageUploadView,
    # which calls core.storage.save_file directly (no new upload mechanism).
    reference_images = models.JSONField(default=list, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)

    # Staff-set quote, adjustable any time before approval.
    quoted_unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    quoted_total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    # Snapshotted the moment the request is approved (see transition_to) so a
    # later pricing-config or PrintArea price change never moves this order's
    # books -- same rule food/orders/settlements already follow.
    agreed_unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    agreed_total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    staff_notes = models.TextField(blank=True, default="")

    chat_thread = models.ForeignKey(
        "chat.ChatThread", on_delete=models.SET_NULL, null=True, blank=True, related_name="print_request",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="print_req_status_created_idx"),
            models.Index(fields=["customer", "-created_at"], name="print_req_customer_created_idx"),
        ]

    def can_transition_to(self, new_status):
        return new_status in self.ALLOWED_TRANSITIONS.get(self.status, set())

    def transition_to(self, new_status, changed_by=None, reason=""):
        """The single choke point for every status write on a PrintRequest --
        every view (customer proof decision, staff proof-attach/price/status
        actions) routes through this, so a status can never be written
        anywhere else (mirrors food.models.FoodOrder.transition_to)."""
        from django.utils import timezone
        from rest_framework.exceptions import ValidationError

        new_status = PrintRequest.Status(new_status)
        if new_status == self.status:
            return self
        if not self.can_transition_to(new_status):
            raise ValidationError(f"Cannot move print request from {self.status} to {new_status}.")
        self.status = new_status
        update_fields = ["status", "updated_at"]

        if new_status == PrintRequest.Status.APPROVED:
            # Snapshot whatever the staff quote currently is. Falls back to a
            # live-computed quote if staff never set one, so approval never
            # silently books a NULL price.
            from printing.services import compute_quote

            if self.quoted_unit_price is not None:
                self.agreed_unit_price = self.quoted_unit_price
                self.agreed_total_price = self.quoted_total_price or (self.quoted_unit_price * self.quantity)
            else:
                quote = compute_quote(self)
                self.agreed_unit_price = quote["unit_price"]
                self.agreed_total_price = quote["total_price"]
            self.approved_at = timezone.now()
            update_fields += ["agreed_unit_price", "agreed_total_price", "approved_at"]

        self.save(update_fields=update_fields)
        return self

    def __str__(self):
        return f"PrintRequest #{self.pk} ({self.status})"


class PrintProof(TimeStamped):
    """A version of the artwork the owner attached. Multiple rows per
    request (one per revision round) -- newest ``version`` wins and is the
    only one a customer may decide on."""

    class Decision(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REVISION_REQUESTED = "REVISION_REQUESTED", "Revision Requested"

    print_request = models.ForeignKey(PrintRequest, on_delete=models.CASCADE, related_name="proofs")
    image = models.URLField(max_length=500)
    version = models.PositiveIntegerField()
    note = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    decision = models.CharField(max_length=20, choices=Decision.choices, default=Decision.PENDING)
    customer_feedback = models.TextField(blank=True, default="")
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(fields=["print_request", "version"], name="unique_proof_version_per_request"),
        ]

    def __str__(self):
        return f"Proof v{self.version} for request #{self.print_request_id} ({self.decision})"


class PrintRosterLine(TimeStamped):
    """A team/jersey order's player row -- child of a PrintRequest, not free
    text, so the owner gets a structured list to print from."""

    print_request = models.ForeignKey(PrintRequest, on_delete=models.CASCADE, related_name="roster_lines")
    player_name = models.CharField(max_length=120)
    number = models.CharField(max_length=10, blank=True, default="")
    size = models.CharField(max_length=10, choices=SIZE_CHOICES, blank=True, default="")
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.player_name} #{self.number} ({self.size}) x{self.quantity}"


class PrintShowcaseItem(TimeStamped):
    """A garment/product shown on the public Custom Printing page so a client
    can see what we can print before writing a brief.

    Separate from ``PrintablePreset`` on purpose: a preset is a *sellable*
    configuration with sizes, colours and a base price that a request can be
    submitted against, while a showcase item is purely a picture and a name
    ("we can also do mugs, caps, tote bags"). Conflating them would force the
    owner to invent sizes and prices for a coffee mug just to show it exists.

    ``image`` is a URL produced by the normal upload endpoint
    (``POST /api/uploads/`` -> ``core.storage.save_file`` -> a content-addressed
    ``core.ImageBlob`` served from ``/api/media/<sha>/``), so showcase photos
    survive Render's ephemeral filesystem like every other image here. Blank is
    allowed -- the page falls back to a typographic tile.
    """

    CATEGORY_CHOICES = [
        ("apparel", "Apparel"),
        ("headwear-bags", "Headwear & bags"),
        ("drinkware", "Drinkware"),
        ("office", "Office & stationery"),
        ("accessories-tech", "Accessories & tech"),
    ]

    name = models.CharField(max_length=120)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default="apparel")
    note = models.CharField(max_length=160, blank=True, default="")
    image = models.URLField(max_length=500, blank=True, default="")
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name
