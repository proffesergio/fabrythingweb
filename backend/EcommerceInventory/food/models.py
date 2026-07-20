import uuid
from django.db import models
from django.conf import settings
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
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("15.00"))
    base_delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    avg_prep_minutes = models.PositiveIntegerField(default=30)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    is_open = models.BooleanField(default=True)
    zones = models.ManyToManyField(DeliveryZone, through="RestaurantZone", related_name="restaurants")

    class Meta:
        indexes = [models.Index(fields=["slug"]), models.Index(fields=["status"])]

    def payout_for(self, subtotal):
        subtotal = Decimal(subtotal)
        return (subtotal * (Decimal("100") - self.commission_percentage) / Decimal("100")).quantize(Decimal("0.01"))

    def is_currently_open(self, now):
        if not self.is_open:
            return False
        hours = self.hours.filter(weekday=now.weekday(), is_closed=False)
        t = now.time()
        return any(h.open_time <= t <= h.close_time for h in hours)

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
    spice_level = models.CharField(max_length=20, blank=True, default="")
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=["restaurant", "is_available"])]
        constraints = [models.UniqueConstraint(fields=["restaurant", "slug"], name="uniq_item_slug_per_restaurant")]

    @property
    def effective_price(self):
        return self.discount_price if self.discount_price is not None else self.price


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
    order_code = models.CharField(max_length=12, unique=True, default=generate_food_order_code)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLACED)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
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
