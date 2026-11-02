import uuid
from datetime import timedelta
from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from food.geo import haversine_km


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class DeliveryZone(TimeStamped):
    name = models.CharField(max_length=120)
    name_bn = models.CharField(max_length=120, blank=True, default="")
    center_lat = models.DecimalField(max_digits=9, decimal_places=6)
    center_lng = models.DecimalField(max_digits=9, decimal_places=6)
    radius_km = models.DecimalField(max_digits=5, decimal_places=2, default=3)
    is_active = models.BooleanField(default=True)

    def serves(self, lat, lng):
        return haversine_km(self.center_lat, self.center_lng, lat, lng) <= float(self.radius_km)

    def __str__(self):
        return self.name


class DeliveryPricing(TimeStamped):
    """The knobs for distance-based delivery pricing. Exactly one row.

    These are rates, not money owed, so they live in the database rather than in
    settings: the owner tunes fuel-sensitive numbers from the admin panel
    without a deploy. Nothing reads this at *settlement* time — every figure is
    snapshotted onto the order when it is placed (food/pricing.py), so changing
    a rate here never moves an existing order's books.

    The distance-based rule, per order:

        billable_km = max(0, distance_km - free_km)
        fee         = clamp(base_fee + per_km_fee * billable_km, min_fee, max_fee)
        rider_pay   = rider_base_pay + rider_per_km * billable_km

    `per_km_fee > rider_per_km` is what makes a longer delivery *more* profitable
    rather than less. `platform_min_margin` is the backstop that holds even if
    someone misconfigures that — see pricing.delivery_quote.
    """

    base_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("30.00"))
    free_km = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("2.00"))
    per_km_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("12.00"))
    min_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("30.00"))
    max_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("150.00"))

    rider_base_pay = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("25.00"))
    rider_per_km = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("8.00"))

    # The platform must never pay a rider more than it collected for delivery.
    # This is the hard floor on (delivery_fee - rider_base_pay).
    platform_min_margin = models.DecimalField(max_digits=10, decimal_places=2,
                                              default=Decimal("5.00"))

    # Cash country: quote round numbers. 5 means every fee is a multiple of ৳5.
    round_to_nearest = models.PositiveIntegerField(default=5)

    # Beyond this, the order is refused rather than quoted. Without it, a very
    # long delivery hits max_fee, the margin backstop then claws back the
    # rider's pay, and the rider silently eats the distance.
    max_delivery_km = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("12.00"))

    # A rider holding more than this much undeposited COD cash stops being
    # offered new cash orders. See services_cash.py.
    rider_cash_ceiling = models.DecimalField(max_digits=10, decimal_places=2,
                                             default=Decimal("3000.00"))

    class Meta:
        verbose_name_plural = "Delivery pricing"

    @classmethod
    def get_solo(cls):
        """The single config row, created with defaults on first use."""
        obj = cls.objects.order_by("id").first()
        return obj or cls.objects.create()

    def __str__(self):
        return f"Delivery pricing (base ৳{self.base_fee} + ৳{self.per_km_fee}/km)"


class Village(TimeStamped):
    """A village inside a DeliveryZone (union). Delivery is restricted to these;
    the fee is inherited from the parent zone/union via RestaurantZone."""
    zone = models.ForeignKey(DeliveryZone, on_delete=models.CASCADE, related_name="villages")
    name = models.CharField(max_length=120)
    name_bn = models.CharField(max_length=120, blank=True, default="")
    # Optional, and worth filling in: distance-based delivery pricing falls back
    # to the parent zone's centre when a village has no centre of its own and the
    # customer dropped no pin, which can be several km off inside a large union.
    center_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    center_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("zone", "name")

    def __str__(self):
        return f"{self.name} ({self.zone.name})"


class Restaurant(TimeStamped):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACTIVE = "ACTIVE", "Active"
        SUSPENDED = "SUSPENDED", "Suspended"
        REJECTED = "REJECTED", "Rejected"

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="restaurant",
    )
    name = models.CharField(max_length=150)
    name_bn = models.CharField(max_length=150, blank=True, default="")
    slug = models.SlugField(max_length=170, unique=True)
    description = models.TextField(blank=True, default="")
    description_bn = models.TextField(blank=True, default="")
    logo = models.URLField(max_length=500, blank=True, default="")
    cover_image = models.URLField(max_length=500, blank=True, default="")
    cuisine_type = models.CharField(max_length=120, blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    address = models.CharField(max_length=255, blank=True, default="")
    pickup_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pickup_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("12.00"))
    # A floor under the percentage. On a ৳150 rural order, 12% is ৳18 — less than
    # a rider costs, so a pure percentage loses money on exactly the orders this
    # platform gets most of. Commission is max(this, percentage), so small orders
    # pay their way and large ones still scale. Per-restaurant, so a partner can
    # be negotiated individually. See food/pricing.py.
    min_commission_amount = models.DecimalField(max_digits=10, decimal_places=2,
                                                default=Decimal("25.00"))
    base_delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    avg_prep_minutes = models.PositiveIntegerField(default=30)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    is_open = models.BooleanField(default=True)
    is_accepting_orders = models.BooleanField(default=True)  # "busy" pause without going offline
    zones = models.ManyToManyField(DeliveryZone, through="RestaurantZone", related_name="restaurants")

    class Meta:
        indexes = [models.Index(fields=["slug"]), models.Index(fields=["status"])]

    def payout_for(self, subtotal):
        subtotal = Decimal(subtotal)
        return (subtotal * (Decimal("100") - self.commission_percentage) / Decimal("100")).quantize(Decimal("0.01"))

    def is_currently_open(self, now):
        if not self.is_open:
            return False
        # Filtered in Python, not with .filter(): the list endpoints serialize this
        # for every row, and a queryset .filter() ignores prefetch_related and
        # re-queries per restaurant (a textbook N+1). Iterating .all() uses the
        # prefetch cache when there is one and costs a single query when there
        # isn't. A restaurant has at most 7 hours rows, so this is free.
        t = now.time()
        weekday = now.weekday()
        return any(h.open_time <= t <= h.close_time
                   for h in self.hours.all()
                   if h.weekday == weekday and not h.is_closed)

    def next_opening(self, now):
        """When this restaurant next opens: ``{weekday, open_time, days_ahead}``.

        None means "no answer to give" — the master switch is off, or no hours
        have been configured at all. The menu tells the customer *when* to come
        back rather than a bare "Closed", so this walks forward up to 7 days
        from ``now``. Iterates ``hours.all()`` for the same prefetch reason as
        is_currently_open().
        """
        if not self.is_open:
            return None
        rows = [h for h in self.hours.all() if not h.is_closed]
        if not rows:
            return None
        t, today = now.time(), now.weekday()
        for days_ahead in range(8):
            weekday = (today + days_ahead) % 7
            for h in sorted((h for h in rows if h.weekday == weekday), key=lambda h: h.open_time):
                # Today only counts if the doors have not opened yet; a slot
                # already in progress means is_currently_open() is True anyway.
                if days_ahead > 0 or h.open_time > t:
                    return {"weekday": weekday, "open_time": h.open_time, "days_ahead": days_ahead}
        return None

    def __str__(self):
        return self.name


class RestaurantHours(TimeStamped):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="hours")
    weekday = models.PositiveSmallIntegerField()  # 0=Mon .. 6=Sun (datetime.weekday())
    open_time = models.TimeField()
    close_time = models.TimeField()
    is_closed = models.BooleanField(default=False)


class RestaurantZone(TimeStamped):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="restaurant_zones")
    zone = models.ForeignKey(DeliveryZone, on_delete=models.CASCADE, related_name="zone_restaurants")
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ("restaurant", "zone")


class FoodCategory(TimeStamped):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=120)
    name_bn = models.CharField(max_length=120, blank=True, default="")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["restaurant", "display_order"])]


class FoodItem(TimeStamped):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="items")
    category_id = models.ForeignKey(FoodCategory, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=150)
    name_bn = models.CharField(max_length=150, blank=True, default="")
    slug = models.SlugField(max_length=170)
    description = models.TextField(blank=True, default="")
    description_bn = models.TextField(blank=True, default="")
    image = models.URLField(max_length=500, blank=True, default="")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    prep_minutes = models.PositiveIntegerField(null=True, blank=True)
    is_available = models.BooleanField(default=True)
    is_veg = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)  # "Bestseller" / chef's pick
    tags = models.JSONField(default=list, blank=True)  # curated keys: spicy,new,popular,veg,bestseller
    available_from = models.TimeField(null=True, blank=True)  # e.g. 08:00 (breakfast)
    available_to = models.TimeField(null=True, blank=True)    # e.g. 11:00
    available_days = models.JSONField(default=list, blank=True)  # weekday ints 0-6; empty = every day
    spice_level = models.CharField(max_length=20, blank=True, default="")
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=["restaurant", "is_available"])]
        constraints = [models.UniqueConstraint(fields=["restaurant", "slug"], name="uniq_item_slug_per_restaurant")]

    @property
    def effective_price(self):
        return self.discount_price if self.discount_price is not None else self.price

    def is_available_now(self, now):
        """Available considering the on/off flag AND any schedule window/weekdays."""
        if not self.is_available:
            return False
        if self.available_days and now.weekday() not in self.available_days:
            return False
        if self.available_from and self.available_to:
            t = now.time()
            if self.available_from <= self.available_to:
                return self.available_from <= t <= self.available_to
            return t >= self.available_from or t <= self.available_to  # overnight window
        return True


class FoodItemOptionGroup(TimeStamped):
    item = models.ForeignKey(FoodItem, on_delete=models.CASCADE, related_name="option_groups")
    name = models.CharField(max_length=120)
    name_bn = models.CharField(max_length=120, blank=True, default="")
    min_select = models.PositiveSmallIntegerField(default=0)
    max_select = models.PositiveSmallIntegerField(default=1)
    is_required = models.BooleanField(default=False)


class FoodItemOption(TimeStamped):
    group = models.ForeignKey(FoodItemOptionGroup, on_delete=models.CASCADE, related_name="options")
    name = models.CharField(max_length=120)
    name_bn = models.CharField(max_length=120, blank=True, default="")
    price_delta = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_default = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)


class Coupon(TimeStamped):
    """Promo code. restaurant=null → platform-wide (admin). restaurant set → that
    vendor's coupon (created by admin or the vendor)."""
    class DiscountType(models.TextChoices):
        PERCENT = "PERCENT", "Percent"
        FLAT = "FLAT", "Flat"

    code = models.CharField(max_length=32, unique=True)
    restaurant = models.ForeignKey(Restaurant, null=True, blank=True, on_delete=models.CASCADE, related_name="coupons")
    discount_type = models.CharField(max_length=8, choices=DiscountType.choices, default=DiscountType.PERCENT)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # cap for percent
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def discount_for(self, subtotal):
        subtotal = Decimal(subtotal)
        if self.discount_type == self.DiscountType.PERCENT:
            d = subtotal * self.discount_value / Decimal("100")
            if self.max_discount is not None:
                d = min(d, Decimal(self.max_discount))
        else:
            d = Decimal(self.discount_value)
        return min(d, subtotal).quantize(Decimal("0.01"))

    def error_for(self, restaurant, subtotal, now):
        """Return a user-facing error string if not applicable, else None."""
        if not self.is_active:
            return "This coupon is not active."
        if self.restaurant_id and self.restaurant_id != restaurant.id:
            return "This coupon isn't valid for this restaurant."
        if self.valid_from and now < self.valid_from:
            return "This coupon isn't active yet."
        if self.valid_until and now > self.valid_until:
            return "This coupon has expired."
        if Decimal(subtotal) < self.min_order_amount:
            return f"Add more — minimum BDT {self.min_order_amount} for this coupon."
        if self.usage_limit is not None and self.used_count >= self.usage_limit:
            return "This coupon has reached its usage limit."
        return None

    def __str__(self):
        return self.code


def generate_food_order_code():
    return f"FD-{uuid.uuid4().hex[:6].upper()}"


class FoodOrder(TimeStamped):
    """A customer-facing Cash-on-Delivery food order.

    Money is snapshotted at creation (the server-authoritative single source of
    truth) and the status follows a strict forward-only state machine.
    """

    class Status(models.TextChoices):
        PLACED = "PLACED", "Placed"
        CONFIRMED = "CONFIRMED", "Confirmed"
        PREPARING = "PREPARING", "Preparing"
        OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY", "Out for Delivery"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"

    ALLOWED_TRANSITIONS = {
        Status.PLACED: {Status.CONFIRMED, Status.CANCELLED},
        Status.CONFIRMED: {Status.PREPARING, Status.CANCELLED},
        Status.PREPARING: {Status.OUT_FOR_DELIVERY, Status.CANCELLED},
        Status.OUT_FOR_DELIVERY: {Status.DELIVERED, Status.CANCELLED},
        Status.DELIVERED: set(),
        Status.CANCELLED: set(),
    }

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name="food_orders")
    guest_name = models.CharField(max_length=120)
    guest_phone = models.CharField(max_length=20)
    delivery_address = models.TextField()
    restaurant = models.ForeignKey(Restaurant, on_delete=models.PROTECT, related_name="orders")
    zone = models.ForeignKey(DeliveryZone, null=True, blank=True, on_delete=models.SET_NULL,
                             related_name="orders")
    village = models.ForeignKey(Village, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="orders")
    delivery_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    rider = models.ForeignKey("Rider", null=True, blank=True, on_delete=models.SET_NULL, related_name="orders")
    order_code = models.CharField(max_length=12, unique=True, default=generate_food_order_code)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLACED)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    coupon_code = models.CharField(max_length=32, blank=True, default="")
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    # How far the rider actually has to go, and what we promised to pay them for
    # it — both snapshotted at checkout alongside the fee they paid. Settlement
    # reads rider_base_pay from here rather than recomputing, so a rate change
    # tomorrow cannot alter what a rider is owed for a delivery made today.
    # Null distance means we never knew it (no pin, no village/zone centre); the
    # fee then fell back to the flat per-zone rate.
    distance_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    rider_base_pay = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    tip = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=10, decimal_places=2)
    eta_minutes = models.PositiveIntegerField(default=45)
    payment_method = models.CharField(max_length=8, default="COD")
    payment_status = models.CharField(max_length=12, default="PENDING")  # PENDING | COLLECTED
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["restaurant", "status"]),
            models.Index(fields=["order_code"]),
        ]

    def can_transition_to(self, new_status):
        return new_status in self.ALLOWED_TRANSITIONS.get(self.status, set())

    def transition_to(self, new_status, changed_by=None, reason=""):
        from rest_framework.exceptions import ValidationError
        new_status = FoodOrder.Status(new_status)
        if new_status == self.status:
            return self
        if not self.can_transition_to(new_status):
            raise ValidationError(f"Cannot move order from {self.status} to {new_status}.")
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])

        # Book the money the moment the order lands. This is the one choke point
        # every caller goes through (rider, vendor and admin status views all
        # call transition_to), so the ledger can't be bypassed by adding another
        # endpoint later. Imported here, not at module scope: services_settlement
        # imports this module.
        if new_status == FoodOrder.Status.DELIVERED:
            from food.services_settlement import settle_order
            settle_order(self)
        return self

    def __str__(self):
        return f"{self.order_code} ({self.status})"


class FoodOrderItem(TimeStamped):
    order = models.ForeignKey(FoodOrder, on_delete=models.CASCADE, related_name="items")
    item = models.ForeignKey(FoodItem, null=True, on_delete=models.SET_NULL, related_name="order_items")
    item_name = models.CharField(max_length=150)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    selected_options = models.JSONField(default=list, blank=True)  # [{"name":..., "price_delta":...}]
    line_total = models.DecimalField(max_digits=10, decimal_places=2)


# ── Phase B: Payments ────────────────────────────────────────────────────────
class PaymentTransaction(TimeStamped):
    class Method(models.TextChoices):
        COD = "COD", "Cash on Delivery"
        BKASH = "BKASH", "bKash"
        NAGAD = "NAGAD", "Nagad"
        QR = "QR", "Bangla QR"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    order = models.ForeignKey(FoodOrder, on_delete=models.CASCADE, related_name="payments")
    method = models.CharField(max_length=10, choices=Method.choices, default=Method.COD)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    provider_ref = models.CharField(max_length=100, blank=True, default="")  # gateway/txn id

    def __str__(self):
        return f"{self.order.order_code} {self.method} {self.status}"


# ── Phase C: Riders & dispatch ───────────────────────────────────────────────
def generate_rider_code():
    return f"RD-{uuid.uuid4().hex[:5].upper()}"


class Rider(TimeStamped):
    class Vehicle(models.TextChoices):
        BIKE = "BIKE", "Motorbike"
        CYCLE = "CYCLE", "Bicycle"
        FOOT = "FOOT", "On foot"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="rider")
    rider_code = models.CharField(max_length=12, unique=True, default=generate_rider_code)
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20, blank=True, default="")
    vehicle_type = models.CharField(max_length=8, choices=Vehicle.choices, default=Vehicle.BIKE)
    vehicle_number = models.CharField(max_length=30, blank=True, default="")
    is_available = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    total_deliveries = models.PositiveIntegerField(default=0)

    # Presence. The rider dashboard is a web page, not a native app, so "online"
    # is derived rather than declared: the page posts a heartbeat every ~20s
    # while the rider has the Online switch on. A rider is dispatchable only if
    # is_available AND last_seen_at is inside PRESENCE_WINDOW_MINUTES AND a
    # position is known — closing the tab drops them out with no explicit action.
    PRESENCE_WINDOW_MINUTES = 3

    current_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    is_sharing_location = models.BooleanField(default=True)
    nav_display_enabled = models.BooleanField(default=True)

    @property
    def is_online(self):
        """Mirrors the dispatch filter in services_dispatch.available_riders()
        so the admin panel shows the same presence the dispatcher acts on."""
        if not self.last_seen_at:
            return False
        cutoff = timezone.now() - timedelta(minutes=self.PRESENCE_WINDOW_MINUTES)
        return self.last_seen_at >= cutoff

    def __str__(self):
        return f"{self.name} ({self.rider_code})"


class DeliveryOffer(TimeStamped):
    """One order offered to one rider, with a deadline to answer.

    Replaces silent auto-assignment: a CONFIRMED order is *offered* to the
    nearest eligible rider, who accepts or declines, rather than being handed a
    delivery they never agreed to. An offer that is declined or times out
    cascades to the next rider; when the pool is exhausted the order falls to the
    admin queue (the existing manual-assign screen).

    Invariant enforced in services_dispatch.offer_order, not by the schema
    (SQLite makes a partial unique index awkward): **at most one OFFERED offer
    per order at a time.** Everything else keys off that — accept can assume it
    is the only live offer, and the cascade only creates a new one once the
    previous is resolved.
    """

    class State(models.TextChoices):
        OFFERED = "OFFERED", "Offered"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"
        EXPIRED = "EXPIRED", "Expired"

    order = models.ForeignKey(FoodOrder, on_delete=models.CASCADE, related_name="delivery_offers")
    rider = models.ForeignKey("Rider", on_delete=models.CASCADE, related_name="delivery_offers")
    state = models.CharField(max_length=8, choices=State.choices, default=State.OFFERED)
    offered_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-offered_at"]
        indexes = [models.Index(fields=["state"]), models.Index(fields=["rider", "state"])]

    @property
    def is_live(self):
        return self.state == self.State.OFFERED and self.expires_at > timezone.now()

    def seconds_left(self):
        return max(0, int((self.expires_at - timezone.now()).total_seconds()))

    def __str__(self):
        return f"{self.order.order_code} → {self.rider.name} ({self.state})"


class RiderEarning(TimeStamped):
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name="earnings")
    order = models.ForeignKey(FoodOrder, null=True, on_delete=models.SET_NULL, related_name="rider_earnings")
    base_pay = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    tip = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    payout_status = models.CharField(max_length=10, default="PENDING")  # PENDING | PAID


# ── Phase D: Notifications & loyalty ─────────────────────────────────────────
class Notification(TimeStamped):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="food_notifications")
    title = models.CharField(max_length=150)
    body = models.CharField(max_length=300, blank=True, default="")
    order_code = models.CharField(max_length=12, blank=True, default="")
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]


class LoyaltyAccount(TimeStamped):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="loyalty")
    points = models.PositiveIntegerField(default=0)


class LoyaltyLedger(TimeStamped):
    account = models.ForeignKey(LoyaltyAccount, on_delete=models.CASCADE, related_name="entries")
    delta = models.IntegerField()  # +earn / -redeem
    reason = models.CharField(max_length=120, blank=True, default="")
    order_code = models.CharField(max_length=12, blank=True, default="")


# ── Phase E: Settlement ledger ───────────────────────────────────────────────
class RiderCashDeposit(TimeStamped):
    """Cash a rider handed back to the platform.

    On a COD order the rider collects the customer's money, so between delivery
    and deposit the platform's cash is physically in a rider's pocket. This is
    the record of it coming back.

    Deliberately NOT a balance column on Rider: the amount outstanding is
    derived from the settlement legs still PENDING (see services_cash.
    cash_in_hand), so it can never drift out of step with the ledger the way a
    stored counter would.
    """

    rider = models.ForeignKey("Rider", on_delete=models.PROTECT, related_name="cash_deposits")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="cash_receipts")
    received_at = models.DateTimeField(default=timezone.now)
    note = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-received_at"]

    def __str__(self):
        return f"{self.rider.name} deposited ৳{self.amount}"


class OrderSettlement(TimeStamped):
    """The money breakdown for one delivered order, and who has been paid.

    Every figure is SNAPSHOTTED from the order at delivery time, not computed on
    read: `Restaurant.commission_percentage` and the rider base pay change over
    time, and a past order's books must not move when they do. This mirrors the
    money-is-snapshotted-at-creation rule on FoodOrder itself.

    Four independent money movements hang off a single delivered order, and each
    settles on its own clock:
      1. customer_payment  — the customer's cash/mobile money is in hand
      2. rider_cash        — the rider handed over the COD cash they collected
      3. rider_payout      — we paid the rider their base pay + tips
      4. restaurant_payout — we paid the restaurant their share after commission

    Derivation, all from the order total:
        food_net         = subtotal - discount
        commission       = food_net * commission_rate%        -> platform
        restaurant_payout= food_net - commission              -> restaurant
        rider_payout     = rider_base_pay + tip               -> rider
        platform_revenue = commission + delivery_fee - rider_base_pay
    So: total == restaurant_payout + commission + delivery_fee + tip, and the
    platform keeps `platform_revenue` once the rider and restaurant are paid.
    """

    class Settle(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SETTLED = "SETTLED", "Settled"
        NA = "NA", "Not applicable"

    order = models.OneToOneField(FoodOrder, on_delete=models.CASCADE, related_name="settlement")

    # Snapshotted inputs — never re-read from Restaurant/settings after creation.
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    # The floor that applied when this order settled. Snapshotted for exactly the
    # same reason as the rate: raising the floor next month must not rewrite this
    # month's books.
    commission_floor = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    food_net = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    tip = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    # Derived splits.
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    restaurant_payout = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    rider_base_pay = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    rider_payout = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    platform_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    # Who actually delivered it. Denormalised on purpose: FoodOrder.rider is
    # SET_NULL, so deleting a rider would otherwise erase the delivery record
    # from the books.
    rider = models.ForeignKey("Rider", null=True, blank=True, on_delete=models.SET_NULL,
                              related_name="settlements")
    rider_name = models.CharField(max_length=120, blank=True, default="")

    customer_payment_status = models.CharField(max_length=8, choices=Settle.choices, default=Settle.PENDING)
    rider_cash_status = models.CharField(max_length=8, choices=Settle.choices, default=Settle.PENDING)
    rider_payout_status = models.CharField(max_length=8, choices=Settle.choices, default=Settle.PENDING)
    restaurant_payout_status = models.CharField(max_length=8, choices=Settle.choices, default=Settle.PENDING)

    customer_payment_at = models.DateTimeField(null=True, blank=True)
    rider_cash_at = models.DateTimeField(null=True, blank=True)
    rider_payout_at = models.DateTimeField(null=True, blank=True)
    restaurant_payout_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True, default="")

    # Maps a settlement leg to (status field, timestamp field).
    LEGS = {
        "customer_payment": ("customer_payment_status", "customer_payment_at"),
        "rider_cash": ("rider_cash_status", "rider_cash_at"),
        "rider_payout": ("rider_payout_status", "rider_payout_at"),
        "restaurant_payout": ("restaurant_payout_status", "restaurant_payout_at"),
    }

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer_payment_status"]),
            models.Index(fields=["rider_payout_status"]),
            models.Index(fields=["restaurant_payout_status"]),
        ]

    @property
    def is_fully_settled(self):
        return all(getattr(self, f) in (self.Settle.SETTLED, self.Settle.NA)
                   for f, _ in self.LEGS.values())

    def __str__(self):
        return f"Settlement {self.order.order_code}"


class DeviceToken(TimeStamped):
    class App(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        RIDER = "rider", "Rider"
        RESTAURANT = "restaurant", "Restaurant"

    class Platform(models.TextChoices):
        IOS = "ios", "iOS"
        ANDROID = "android", "Android"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="device_tokens")
    expo_token = models.CharField(max_length=255, unique=True)
    app = models.CharField(max_length=12, choices=App.choices)
    platform = models.CharField(max_length=8, choices=Platform.choices)
    enabled = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["user", "enabled"])]

    def __str__(self):
        return f"{self.app}:{self.expo_token[-8:]}"
