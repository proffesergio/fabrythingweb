"""
Order domain services.

The checkout path lives here (not in a view) so it can be reused and unit
tested. It is the single place where inventory is reserved, and it is the
critical section for preventing oversell under concurrency.
"""
from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from catalog.models import ProductVariant
from core.models import StoreConfiguration

from .models import Order, OrderItem, OrderStatusLog


class OutOfStock(ValidationError):
    status_code = 409


@transaction.atomic
def place_cod_order(*, customer, items, contact_name, contact_phone,
                    shipping_address, notes="", client_ip=None):
    """
    Create a Cash-on-Delivery order.

    ``items`` is a list of {"variant_id": int, "quantity": int}.

    Concurrency safety: every referenced variant row is locked with
    select_for_update() before its stock is checked and decremented, so two
    simultaneous checkouts cannot both sell the last unit. The whole function
    runs in one atomic block — any failure rolls back the order *and* the
    stock decrements together.
    """
    config = StoreConfiguration.get_solo()
    if not config.cod_enabled:
        raise ValidationError("Cash on Delivery is currently unavailable.")

    if not items:
        raise ValidationError("Your cart is empty.")

    # Aggregate requested quantity per variant (guards against duplicate lines).
    requested = {}
    for line in items:
        vid = line.get("variant_id")
        qty = int(line.get("quantity", 0))
        if not vid or qty <= 0:
            raise ValidationError("Each item needs a valid variant_id and quantity.")
        requested[vid] = requested.get(vid, 0) + qty

    # Lock all variant rows up front, in a stable order, to avoid deadlocks.
    variants = {
        v.id: v
        for v in ProductVariant.objects.select_for_update()
        .filter(id__in=requested.keys())
        .order_by("id")
    }

    order_items = []
    subtotal = Decimal("0.00")
    for vid, qty in requested.items():
        variant = variants.get(vid)
        if variant is None or not variant.is_active:
            raise ValidationError(f"Variant {vid} is not available.")
        if variant.stock_quantity < qty:
            raise OutOfStock(
                f"Only {variant.stock_quantity} left of "
                f"{variant.product.name} ({variant.size or 'One size'})."
            )
        unit_price = Decimal(str(variant.effective_price))
        line_total = unit_price * qty
        subtotal += line_total
        order_items.append((variant, qty, unit_price, line_total))

    shipping = config.shipping_for(subtotal)
    total = subtotal + shipping

    order = Order.objects.create(
        customer=customer if getattr(customer, "is_authenticated", False) else None,
        subtotal=subtotal,
        shipping_amount=shipping,
        total_amount=total,
        currency=config.currency,
        contact_name=contact_name,
        contact_phone=contact_phone,
        shipping_address=shipping_address,
        notes=notes or "",
        client_ip=client_ip,
    )

    for variant, qty, unit_price, line_total in order_items:
        OrderItem.objects.create(
            order=order,
            variant=variant,
            product_name=variant.product.name or "",
            sku=variant.sku,
            size=variant.size,
            color=variant.color,
            unit_price=unit_price,
            quantity=qty,
            line_total=line_total,
        )
        # Decrement the locked row.
        variant.stock_quantity -= qty
        variant.save(update_fields=["stock_quantity", "updated_at"])

    OrderStatusLog.objects.create(
        order=order,
        from_status="",
        to_status=Order.Status.PENDING_VERIFICATION,
        changed_by=order.customer,
        reason="Order placed",
    )
    return order
