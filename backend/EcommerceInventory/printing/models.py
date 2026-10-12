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


class PressShopConfig(TimeStamped):
    """Singleton tunable for the web-to-press storefront (ColorLifePrint-style).

    ``usd_rate`` is BDT per 1 USD for the BDT( Vaughan) / USD toggle.
    ``default_margin_factor`` feeds the pricing formula when a product does
    not override it. ``max_upload_mb`` caps artwork uploads (chunked on the
    client; enforced per-file here). ``shipping_matrix`` is the fallback fee
    table when no PressShippingRate row matches.
    """

    usd_rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("117.50"))
    default_margin_factor = models.DecimalField(max_digits=5, decimal_places=3, default=Decimal("1.250"))
    max_upload_mb = models.PositiveIntegerField(default=100)
    currency_default = models.CharField(max_length=3, default="BDT")
    shipping_matrix = models.JSONField(
        default=dict, blank=True,
        help_text='Fallback {"inside_dhaka_home": 80, "hub_pickup": 0, '
                  '"outside_dhaka": 130, "per_kg": 20} in BDT.',
    )

    @classmethod
    def get_solo(cls):
        obj = cls.objects.order_by("id").first()
        if obj:
            return obj
        return cls.objects.create(
            shipping_matrix={"inside_dhaka_home": 80, "hub_pickup": 0, "outside_dhaka": 130, "per_kg": 20},
        )

    def __str__(self):
        return "Press shop config"


class PressProduct(TimeStamped):
    """A web-to-press sellable (Business Cards, Flyers, PVC Banners...).

    Pricing follows the spec formula::

        Total = (Base Setup + Per-Unit Material * Qty + Finishing Add-ons) * Margin

    with the quantity-tier discount (PrintPricingConfig ladder, overridable
    per product via ``quantity_tiers``) applied to the material leg before the
    margin factor. All money is stored in BDT; USD is a display conversion.
    """

    CATEGORY_CHOICES = [
        ("cards", "Cards"),
        ("flyers", "Flyers & Leaflets"),
        ("banners", "Banners & Large Format"),
        ("office", "Office & Stationery"),
        ("packaging", "Packaging & Labels"),
        ("corporate", "Corporate & Gifts"),
    ]

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default="cards")
    description = models.TextField(blank=True, default="")
    image = models.URLField(max_length=500, blank=True, default="")

    base_setup_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    per_unit_material_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0"),
        help_text="Base material cost per unit at 1 sq-inch reference; "
                  "scaled by area ratio at quote time.",
    )
    per_sq_inch_rate = models.DecimalField(
        max_digits=10, decimal_places=4, default=Decimal("0"),
        help_text="BDT per square inch of finished size. When > 0 it takes "
                  "precedence over per_unit_material_cost for area scaling.",
    )
    margin_factor = models.DecimalField(
        max_digits=5, decimal_places=3, null=True, blank=True,
        help_text="NULL means fall back to PressShopConfig.default_margin_factor.",
    )
    quantity_tiers = models.JSONField(
        null=True, blank=True,
        help_text='Optional per-product override of the global ladder, same '
                  'shape: [{"min_qty": int, "discount_percent": number}].',
    )
    min_qty = models.PositiveIntegerField(default=1)
    allow_custom_size = models.BooleanField(default=True)
    allowed_extensions = models.JSONField(
        default=list, blank=True,
        help_text='Defaults to pdf/ai/psd/eps/tiff/png/jpeg when empty.',
    )
    weight_per_unit_kg = models.DecimalField(max_digits=8, decimal_places=3, default=Decimal("0.050"))

    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]

    def effective_margin(self):
        if self.margin_factor is not None:
            return Decimal(self.margin_factor)
        return PressShopConfig.get_solo().default_margin_factor

    def __str__(self):
        return self.name


class PressSizePreset(TimeStamped):
    """Standard size for a product (A4, A5, 3.5"x2") + custom fallback."""

    UNIT_CHOICES = [("in", "Inches"), ("ft", "Feet"), ("mm", "Millimetres")]

    product = models.ForeignKey(PressProduct, on_delete=models.CASCADE, related_name="size_presets")
    name = models.CharField(max_length=80)
    width = models.DecimalField(max_digits=8, decimal_places=2)
    height = models.DecimalField(max_digits=8, decimal_places=2)
    unit = models.CharField(max_length=4, choices=UNIT_CHOICES, default="in")
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]

    def area_sq_inch(self):
        from printing.services_press import to_sq_inch

        return to_sq_inch(self.width, self.height, self.unit)

    def __str__(self):
        return f"{self.product.name} — {self.name}"


class PaperStock(TimeStamped):
    """Paper / media catalogue: 120gsm Art Paper, 300gsm Art Card, PVC..."""

    name = models.CharField(max_length=120, unique=True)
    gsm = models.CharField(max_length=40, blank=True, default="")
    multiplier = models.DecimalField(
        max_digits=6, decimal_places=3, default=Decimal("1.000"),
        help_text="Multiplies the product's material leg (premium stocks > 1).",
    )
    flat_addon_per_unit = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name


class FinishingOption(TimeStamped):
    """Side + lamination + finishing matrix.

    kind=SIDE is single/double sided (4/0, 4/4); kind=LAMINATION is
    glossy/matte/spot-uv; kind=FINISHING is die-cut/crease/foil/...
    ``pricing`` is flat BDT per order when ``per_unit`` is False, else per unit.
    """

    KIND_CHOICES = [("SIDE", "Printing Side"), ("LAMINATION", "Lamination"), ("FINISHING", "Finishing")]

    kind = models.CharField(max_length=12, choices=KIND_CHOICES, default="FINISHING")
    name = models.CharField(max_length=120)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    per_unit = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["kind", "display_order", "name"]

    def __str__(self):
        scope = "/unit" if self.per_unit else "/order"
        return f"{self.name} (+{self.price}{scope})"


class PressShippingRate(TimeStamped):
    """Weight + location based courier fees for Bangladesh.

    zone INSIDE_DHAKA_HOME (Pathao/Steadfast home delivery), HUB_PICKUP (free
    pickup), OUTSIDE_DHAKA (Sundarban/SA Paribahan/Paperfly).
    fee = base_fee + per_kg_fee * billable_weight_kg.
    """

    ZONE_CHOICES = [
        ("INSIDE_DHAKA_HOME", "Inside Dhaka — Home Delivery"),
        ("HUB_PICKUP", "Hub Pickup"),
        ("OUTSIDE_DHAKA", "Outside Dhaka — Courier"),
    ]

    zone = models.CharField(max_length=20, choices=ZONE_CHOICES)
    courier = models.CharField(max_length=80, default="")
    base_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    per_kg_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["zone", "base_fee"]

    def quote_for(self, weight_kg):
        return Decimal(self.base_fee) + Decimal(self.per_kg_fee) * Decimal(weight_kg)

    def __str__(self):
        return f"{self.get_zone_display()} via {self.courier or '—'} (base {self.base_fee})"


class PressOrder(TimeStamped):
    """A web-to-press checkout: priced configuration + artwork + fulfilment.

    Kept separate from PrintRequest (garment brief/proof loop) on purpose:
    different pricing engine (matrix formula), different fulfilment matrix
    (payment -> artwork review -> production -> dispatch -> shipped ->
    delivered), different admin surface. Nothing here touches the garment
    proof loop and vice versa.
    """

    class Status(models.TextChoices):
        PENDING_PAYMENT = "PENDING_PAYMENT", "Pending Payment"
        ARTWORK_REVIEW = "ARTWORK_REVIEW", "Artwork Review"
        IN_PRODUCTION = "IN_PRODUCTION", "In Production"
        READY_FOR_DISPATCH = "READY_FOR_DISPATCH", "Ready for Dispatch"
        SHIPPED = "SHIPPED", "Shipped"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"

    ALLOWED_TRANSITIONS = {
        Status.PENDING_PAYMENT: {Status.ARTWORK_REVIEW, Status.CANCELLED},
        Status.ARTWORK_REVIEW: {Status.IN_PRODUCTION, Status.CANCELLED},
        Status.IN_PRODUCTION: {Status.READY_FOR_DISPATCH, Status.CANCELLED},
        Status.READY_FOR_DISPATCH: {Status.SHIPPED, Status.CANCELLED},
        Status.SHIPPED: {Status.DELIVERED, Status.CANCELLED},
        Status.DELIVERED: set(),
        Status.CANCELLED: set(),
    }

    PAYMENT_METHODS = [
        ("SSLCOMMERZ", "SSLCommerz"),
        ("BKASH", "bKash"),
        ("NAGAD", "Nagad"),
        ("ROCKET", "Rocket"),
        ("COD", "Cash on Delivery"),
        ("PARTIAL_ADVANCE", "Partial Advance (corporate)"),
    ]
    PAYMENT_STATUS = [
        ("PENDING", "Pending"),
        ("PARTIAL", "Partially Paid"),
        ("PAID", "Paid"),
        ("FAILED", "Failed"),
        ("COD_DUE", "COD — Due on Delivery"),
    ]
    CURRENCIES = [("BDT", "BDT (৳)"), ("USD", "USD ($)")]

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="press_orders",
    )
    product = models.ForeignKey(PressProduct, on_delete=models.PROTECT, related_name="press_orders")
    paper_stock = models.ForeignKey(
        PaperStock, on_delete=models.SET_NULL, null=True, blank=True, related_name="press_orders",
    )
    finishing_options = models.ManyToManyField(FinishingOption, blank=True, related_name="press_orders")

    # Size snapshot (presets can be edited later; the order keeps what was priced).
    size_name = models.CharField(max_length=80, default="")
    width = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    height = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    size_unit = models.CharField(max_length=4, default="in")
    sides = models.CharField(max_length=8, default="4/0")
    quantity = models.PositiveIntegerField(default=1)

    # Priced breakdown snapshot (BDT) — recomputed never; see services_press.
    price_breakdown = models.JSONField(default=dict, blank=True)
    total_bdt = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    currency = models.CharField(max_length=3, choices=CURRENCIES, default="BDT")
    total_charged = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"),
        help_text="What the customer actually pays in `currency`.",
    )

    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default="SSLCOMMERZ")
    payment_status = models.CharField(max_length=12, choices=PAYMENT_STATUS, default="PENDING")
    payment_txn_id = models.CharField(max_length=120, blank=True, default="")

    shipping_zone = models.CharField(max_length=20, default="INSIDE_DHAKA_HOME")
    shipping_courier = models.CharField(max_length=80, blank=True, default="")
    shipping_fee_bdt = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    shipping_address = models.JSONField(default=dict, blank=True)

    # Artwork: list of {"url", "name", "size", "content_type"} + validation report.
    artwork_files = models.JSONField(default=list, blank=True)
    artwork_validation = models.JSONField(default=dict, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_PAYMENT)
    staff_notes = models.TextField(blank=True, default="")
    is_corporate = models.BooleanField(default=False)
    po_number = models.CharField(max_length=80, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="press_order_status_created_idx"),
            models.Index(fields=["customer", "-created_at"], name="press_ord_cust_created_idx"),
        ]

    def can_transition_to(self, new_status):
        return new_status in self.ALLOWED_TRANSITIONS.get(self.status, set())

    def transition_to(self, new_status):
        from rest_framework.exceptions import ValidationError

        new_status = PressOrder.Status(new_status)
        if new_status == self.status:
            return self
        if not self.can_transition_to(new_status):
            raise ValidationError(f"Cannot move press order from {self.status} to {new_status}.")
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])
        return self

    def __str__(self):
        return f"PressOrder #{self.pk} ({self.status})"


class CorporateAccount(TimeStamped):
    """Trusted corporate buyer: POs, partial advances and a running ledger."""

    customer = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="corporate_account",
    )
    company_name = models.CharField(max_length=180)
    contact_phone = models.CharField(max_length=40, blank=True, default="")
    billing_address = models.TextField(blank=True, default="")
    credit_limit_bdt = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    ledger_balance_bdt = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"),
        help_text="Positive = customer owes us.",
    )
    trusted_for_partial = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.company_name} ({self.customer})"


class Quotation(TimeStamped):
    """Automated quotation PDF payload for a press configuration.

    A draft snapshot of a would-be PressOrder (no fulfilment side effects).
    Accepting it is a client-side checkout prefill; the real order is created
    through the normal press checkout endpoint with ``quotation_id`` attached.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SENT = "SENT", "Sent"
        ACCEPTED = "ACCEPTED", "Accepted"
        ORDERED = "ORDERED", "Ordered"
        EXPIRED = "EXPIRED", "Expired"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="press_quotations",
    )
    product = models.ForeignKey(PressProduct, on_delete=models.PROTECT, related_name="quotations")
    config_snapshot = models.JSONField(default=dict, blank=True)
    price_breakdown = models.JSONField(default=dict, blank=True)
    total_bdt = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    currency = models.CharField(max_length=3, default="BDT")
    po_number = models.CharField(max_length=80, blank=True, default="")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    press_order = models.ForeignKey(
        PressOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name="quotations",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Quotation #{self.pk} ({self.status})"


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

    # Garment keys feed the t-shirt custom-request showcase; press keys feed
    # the ColorLifePrint-style storefront (category strip + Top Picks).
    CATEGORY_CHOICES = [
        ("apparel", "Apparel"),
        ("headwear-bags", "Headwear & bags"),
        ("drinkware", "Drinkware"),
        ("office", "Office & stationery"),
        ("accessories-tech", "Accessories & tech"),
        ("business-cards", "Business Cards"),
        ("flyers-brochures", "Flyers & Brochures"),
        ("brochures-catalogues", "Brochures & Catalogues"),
        ("office-packaging", "Office & Packaging"),
        ("box-packaging", "Box & Packaging"),
        ("stickers-labels", "Stickers & Labels"),
        ("signage-outdoor", "Signage & Outdoor Branding"),
        ("flags-display", "Flags & Outdoor Display"),
        ("large-format", "Large Format Printing"),
        ("corporate-stationery", "Corporate Stationery"),
        ("letterheads", "Letterheads"),
        ("posters", "Posters"),
        ("promotional", "Promotional Products"),
    ]

    BADGE_CHOICES = [
        ("", "None"),
        ("HOT", "Hot"),
        ("NEW", "New"),
        ("OFFER", "Offer"),
    ]

    name = models.CharField(max_length=120)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default="apparel")
    note = models.CharField(max_length=160, blank=True, default="")
    description = models.TextField(blank=True, default="")
    image = models.URLField(
        max_length=500, blank=True, default="",
        help_text="Preview thumbnail. For image uploads this is the file itself.",
    )
    # Full design file in any print format (pdf/ai/psd/eps/tiff/png/jpeg...).
    file_url = models.URLField(max_length=500, blank=True, default="")
    file_type = models.CharField(max_length=12, blank=True, default="")
    badge = models.CharField(max_length=8, choices=BADGE_CHOICES, default="", blank=True)
    price_bdt = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_top_pick = models.BooleanField(default=False)
    press_product = models.ForeignKey(
        PressProduct, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="showcase_items",
        help_text="Orderable press product this design showcases (Order-now handoff).",
    )
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name
