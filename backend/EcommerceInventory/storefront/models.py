from django.conf import settings
from django.db import models


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
