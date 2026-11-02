import uuid

from django.conf import settings
from django.db import models, transaction


def generate_order_number():
    return f"ORD-{uuid.uuid4().hex[:8].upper()}"


class Order(models.Model):
    """
    A customer-facing Cash-on-Delivery order.

    This is deliberately separate from the back-office purchasing.SalesOrder /
    PurchaseOrder inventory documents. It owns a strict COD status state
    machine and snapshots all money + address data at creation time so history
    is immutable even if products/prices later change.
    """

    class Status(models.TextChoices):
        PENDING_VERIFICATION = "PENDING_VERIFICATION", "Pending Verification"
        CONFIRMED = "CONFIRMED", "Confirmed"
        OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY", "Out for Delivery"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELED = "CANCELED", "Canceled"
        RETURNED = "RETURNED", "Returned"

    # Allowed forward transitions. Anything not listed is rejected.
    ALLOWED_TRANSITIONS = {
        Status.PENDING_VERIFICATION: {Status.CONFIRMED, Status.CANCELED},
        Status.CONFIRMED: {Status.OUT_FOR_DELIVERY, Status.CANCELED},
        Status.OUT_FOR_DELIVERY: {Status.DELIVERED, Status.CANCELED, Status.RETURNED},
        Status.DELIVERED: {Status.RETURNED},
        Status.CANCELED: set(),
        Status.RETURNED: set(),
    }

    # Statuses that release reserved stock back to inventory.
    RESTOCK_STATUSES = {Status.CANCELED, Status.RETURNED}

    order_number = models.CharField(max_length=20, unique=True, default=generate_order_number)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="orders",
    )
    status = models.CharField(
        max_length=24, choices=Status.choices, default=Status.PENDING_VERIFICATION,
    )
    payment_method = models.CharField(max_length=8, default="COD")

    # Money — all snapshotted at creation, the single source of truth.
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_amount = models.DecimalField(max_digits=8, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="BDT")

    # COD delivery contact — captured at checkout, not read from the profile.
    contact_name = models.CharField(max_length=120)
    contact_phone = models.CharField(max_length=20)
    shipping_address = models.JSONField()  # frozen snapshot of the address
    notes = models.TextField(blank=True, default="")

    # Anti-spam / audit signals.
    client_ip = models.GenericIPAddressField(null=True, blank=True)
    stock_restored = models.BooleanField(default=False)

    canceled_reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["order_number"]),
        ]

    def __str__(self):
        return f"{self.order_number} ({self.status})"

    def can_transition_to(self, new_status):
        return new_status in self.ALLOWED_TRANSITIONS.get(self.status, set())

    @transaction.atomic
    def transition_to(self, new_status, changed_by=None, reason=""):
        """
        Move the order to ``new_status``, enforcing the state machine and
        releasing stock exactly once on cancel/return.
        """
        new_status = Order.Status(new_status)
        if new_status == self.status:
            return self
        if not self.can_transition_to(new_status):
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                f"Cannot move order from {self.status} to {new_status}."
            )

        old_status = self.status

        if new_status in self.RESTOCK_STATUSES and not self.stock_restored:
            self._restock()
            self.stock_restored = True

        self.status = new_status
        if new_status == Order.Status.CANCELED:
            self.canceled_reason = reason or self.canceled_reason
        self.save(update_fields=["status", "canceled_reason", "stock_restored", "updated_at"])

        OrderStatusLog.objects.create(
            order=self, from_status=old_status, to_status=new_status,
            changed_by=changed_by, reason=reason,
        )
        return self

    def _restock(self):
        """Return each line item's quantity to its variant (row-locked)."""
        from catalog.models import ProductVariant
        for item in self.items.select_related("variant"):
            if item.variant_id is None:
                continue
            ProductVariant.objects.filter(pk=item.variant_id).update(
                stock_quantity=models.F("stock_quantity") + item.quantity
            )


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        "catalog.ProductVariant", null=True, on_delete=models.SET_NULL, related_name="order_items",
    )
    # Snapshots so the line is stable even if the variant/product changes later.
    product_name = models.CharField(max_length=255)
    sku = models.CharField(max_length=64)
    size = models.CharField(max_length=16, blank=True, default="")
    color = models.CharField(max_length=32, blank=True, default="")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product_name} ({self.sku})"


class OrderStatusLog(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_logs")
    from_status = models.CharField(max_length=24)
    to_status = models.CharField(max_length=24)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
    )
    reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.order.order_number}: {self.from_status} -> {self.to_status}"
