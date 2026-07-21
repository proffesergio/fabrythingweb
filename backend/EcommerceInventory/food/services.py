"""Food checkout service — the single server-authoritative pricing/validation path.

Totals are recomputed here from live DB rows, never taken from the client. One
restaurant per order. Handles busy-mode, scheduled item availability, coupons,
loyalty redemption/earning, payment records, and order notifications.
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from food.models import (Restaurant, FoodItem, FoodItemOption, DeliveryZone, RestaurantZone,
                         FoodOrder, FoodOrderItem, Coupon, PaymentTransaction,
                         Notification, LoyaltyAccount, LoyaltyLedger)

DELIVERY_BUFFER_MINUTES = 20
POINTS_PER_BDT = Decimal("50")   # 1 point per ৳50 spent
ONLINE_METHODS = {"BKASH", "NAGAD", "QR"}


def _resolve_zone(restaurant, zone_id, lat, lng):
    served = DeliveryZone.objects.filter(is_active=True, zone_restaurants__restaurant=restaurant)
    if zone_id:
        zone = served.filter(id=zone_id).first()
        if not zone:
            raise ValidationError("This restaurant does not deliver to the selected area.")
        return zone
    if lat is not None and lng is not None:
        for zone in served:
            if zone.serves(lat, lng):
                return zone
        raise ValidationError("Your location is outside this restaurant's delivery area.")
    raise ValidationError("A delivery area is required.")


def _delivery_fee(restaurant, zone):
    rz = RestaurantZone.objects.filter(restaurant=restaurant, zone=zone).first()
    if rz and rz.delivery_fee is not None:
        return Decimal(rz.delivery_fee)
    return Decimal(restaurant.base_delivery_fee)


def notify(user, title, body="", order_code=""):
    if user and getattr(user, "is_authenticated", False):
        Notification.objects.create(user=user, title=title, body=body, order_code=order_code)


def _award_points(user, order):
    if not (user and getattr(user, "is_authenticated", False)):
        return
    pts = int(Decimal(order.subtotal) / POINTS_PER_BDT)
    if pts <= 0:
        return
    acct, _ = LoyaltyAccount.objects.get_or_create(user=user)
    acct.points += pts
    acct.save(update_fields=["points", "updated_at"])
    LoyaltyLedger.objects.create(account=acct, delta=pts, reason="Order reward", order_code=order.order_code)


@transaction.atomic
def place_food_cod_order(*, customer, restaurant_slug, items, contact_name, contact_phone,
                         delivery_address, zone_id=None, lat=None, lng=None, tip="0.00",
                         notes="", coupon_code="", payment_method="COD", redeem_points=0):
    if not items:
        raise ValidationError("Your cart is empty.")
    now = timezone.localtime()

    restaurant = Restaurant.objects.filter(slug=restaurant_slug,
                                           status=Restaurant.Status.ACTIVE).first()
    if not restaurant:
        raise ValidationError("Restaurant is not available.")
    if not restaurant.is_currently_open(now):
        raise ValidationError("This restaurant is currently closed.")
    if not restaurant.is_accepting_orders:
        raise ValidationError("This restaurant is too busy to take orders right now.")

    zone = _resolve_zone(restaurant, zone_id, lat, lng)

    subtotal = Decimal("0.00")
    built = []
    for line in items:
        item_id = line.get("item_id")
        qty = int(line.get("quantity", 0))
        if not item_id or qty <= 0:
            raise ValidationError("Each cart line needs an item and a positive quantity.")
        item = FoodItem.objects.filter(id=item_id, restaurant=restaurant).first()
        if not item or not item.is_available_now(now):
            raise ValidationError("One of the items is not available right now.")
        unit = Decimal(item.effective_price)
        opts = []
        for oid in line.get("option_ids", []):
            opt = FoodItemOption.objects.filter(id=oid, group__item=item).first()
            if not opt:
                raise ValidationError("An invalid option was selected.")
            unit += Decimal(opt.price_delta)
            opts.append({"name": opt.name, "price_delta": str(opt.price_delta)})
        line_total = (unit * qty).quantize(Decimal("0.01"))
        subtotal += line_total
        built.append((item, qty, unit, opts, line_total))

    if subtotal < Decimal(restaurant.min_order_amount):
        raise ValidationError(f"Minimum order is BDT {restaurant.min_order_amount}. Add more items.")

    # Coupon
    discount = Decimal("0.00")
    coupon = None
    if coupon_code:
        coupon = Coupon.objects.select_for_update().filter(code__iexact=coupon_code.strip()).first()
        if not coupon:
            raise ValidationError("Invalid coupon code.")
        err = coupon.error_for(restaurant, subtotal, now)
        if err:
            raise ValidationError(err)
        discount += coupon.discount_for(subtotal)

    # Loyalty redemption (1 point = ৳1), only for logged-in customers with a balance.
    is_auth = getattr(customer, "is_authenticated", False)
    points_used = 0
    if redeem_points and is_auth:
        acct, _ = LoyaltyAccount.objects.select_for_update().get_or_create(user=customer)
        cap = int(min(Decimal(redeem_points), acct.points, subtotal - discount))
        if cap > 0:
            points_used = cap
            discount += Decimal(cap)
            acct.points -= cap
            acct.save(update_fields=["points", "updated_at"])
            LoyaltyLedger.objects.create(account=acct, delta=-cap, reason="Redeemed at checkout")

    discount = min(discount, subtotal).quantize(Decimal("0.01"))
    delivery_fee = _delivery_fee(restaurant, zone)
    tip_amount = Decimal(str(tip or "0.00"))
    total = (subtotal - discount + delivery_fee + tip_amount).quantize(Decimal("0.01"))

    method = (payment_method or "COD").upper()
    if method not in {"COD"} | ONLINE_METHODS:
        method = "COD"

    order = FoodOrder.objects.create(
        customer=customer if is_auth else None,
        guest_name=contact_name, guest_phone=contact_phone, delivery_address=delivery_address,
        restaurant=restaurant, zone=zone, subtotal=subtotal, discount=discount,
        coupon_code=coupon.code if coupon else "", delivery_fee=delivery_fee, tip=tip_amount,
        total=total, notes=notes or "", payment_method=method,
        payment_status="COLLECTED" if method in ONLINE_METHODS else "PENDING",
        eta_minutes=restaurant.avg_prep_minutes + DELIVERY_BUFFER_MINUTES,
    )
    for item, qty, unit, opts, line_total in built:
        FoodOrderItem.objects.create(order=order, item=item, item_name=item.name,
                                     unit_price=unit, quantity=qty, selected_options=opts,
                                     line_total=line_total)

    if coupon:
        coupon.used_count += 1
        coupon.save(update_fields=["used_count", "updated_at"])

    # Payment record (online methods are a sandbox mock → immediately SUCCESS).
    PaymentTransaction.objects.create(
        order=order, method=method, amount=total,
        status=(PaymentTransaction.Status.SUCCESS if method in ONLINE_METHODS
                else PaymentTransaction.Status.PENDING),
        provider_ref=(f"MOCK-{order.order_code}" if method in ONLINE_METHODS else ""),
    )

    _award_points(customer, order)
    notify(customer, "Order placed", f"Your order {order.order_code} is confirmed.", order.order_code)
    return order
