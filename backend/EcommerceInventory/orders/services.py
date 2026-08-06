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
from core.email_alerts import send_email_alert_on_commit
from core.models import StoreConfiguration
from core.whatsapp import send_whatsapp_on_commit

from .models import Order, OrderItem, OrderStatusLog

# Template to create in Meta Business Manager — see the WhatsApp setup report
# for the exact body text/params. Numbered params: order number, customer
# name, customer phone, item count, total (with currency).
STORE_ORDER_ADMIN_TEMPLATE = "store_new_order_admin"


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
    # select_related('product') so reading variant.product.shipping_fee below
    # (and variant.product.name, used further down) doesn't fire a query per line.
    variants = {
        v.id: v
        for v in ProductVariant.objects.select_for_update()
        .select_related('product')
        .filter(id__in=requested.keys())
        .order_by("id")
    }

    order_items = []
    subtotal = Decimal("0.00")
    for vid, qty in requested.items():
        variant = variants.get(vid)
        if variant is None or not variant.is_active:
            raise ValidationError(f"Variant {vid} is not available.")
        # Prescription gate: the owner does not yet hold a DGDA licence, so a
        # requires_prescription product must never be purchasable while
        # StoreConfiguration.rx_sales_enabled is off -- this is the single
        # place checkout resolves/prices a cart line, so putting the guard
        # here (rather than in a view) means no endpoint can bypass it. Not
        # an OutOfStock (409) -- this is a policy block, not a stock issue.
        if variant.product.requires_prescription and not config.rx_sales_enabled:
            raise ValidationError(
                f"{variant.product.name} requires a prescription and is not yet "
                f"available for online purchase."
            )
        if variant.stock_quantity < qty:
            raise OutOfStock(
                f"Only {variant.stock_quantity} left of "
                f"{variant.product.name} ({variant.size or 'One size'})."
            )
        unit_price = Decimal(str(variant.effective_price))
        line_total = unit_price * qty
        subtotal += line_total
        order_items.append((variant, qty, unit_price, line_total))

    # One per-product shipping fee (and free_shipping promo flag) per cart
    # line -- see StoreConfiguration.shipping_for for the full rule (highest
    # per-product fee among non-promo lines, floored at the store's flat
    # rate; an all-promo cart ships free; free-shipping-threshold still wins
    # over all of it).
    product_shipping_fees = [variant.product.shipping_fee for variant, _, _, _ in order_items]
    free_shipping_flags = [variant.product.free_shipping for variant, _, _, _ in order_items]
    shipping = config.shipping_for(subtotal, product_shipping_fees, free_shipping_flags)
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

    # Admin alerts. Both are deferred to after this transaction commits (the
    # atomic block above still holds select_for_update locks on the variant
    # rows) and both are incapable of raising, so a dead mailbox or a
    # misconfigured provider can never roll back an order a customer just
    # placed. Email is the live channel; WhatsApp stays inert until its
    # credentials exist.
    send_email_alert_on_commit(
        (config.alert_email or "").strip(),
        kind="store_order_admin", related_order=order.order_number,
        subject=f"New order {order.order_number} — {total} {config.currency}",
        body=(
            f"A new Cash-on-Delivery order was just placed on {config.store_name}.\n\n"
            f"Order:    {order.order_number}\n"
            f"Customer: {contact_name}\n"
            f"Phone:    {contact_phone}\n"
            f"Items:    {len(order_items)}\n"
            f"Total:    {total} {config.currency}\n\n"
            f"Confirm and arrange delivery from the admin panel:\n"
            f"https://www.fabrything.com/admin/manage/store/orders\n"
        ),
    )

    admin_number = (config.whatsapp_admin_number or "").strip()
    send_whatsapp_on_commit(
        admin_number, kind="store_order_admin", related_order=order.order_number,
        template_name=STORE_ORDER_ADMIN_TEMPLATE,
        params=[order.order_number, contact_name, contact_phone,
               str(len(order_items)), f"{total} {config.currency}"],
    )

    return order
