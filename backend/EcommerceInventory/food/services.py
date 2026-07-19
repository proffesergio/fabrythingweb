"""Food COD checkout service — the single server-authoritative pricing/validation path.

Mirrors orders.services.place_cod_order: totals are recomputed here from live DB rows,
never taken from the client. One restaurant per order.
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from food.models import (Restaurant, FoodItem, FoodItemOption, DeliveryZone,
                         RestaurantZone, FoodOrder, FoodOrderItem)

DELIVERY_BUFFER_MINUTES = 20


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


@transaction.atomic
def place_food_cod_order(*, customer, restaurant_slug, items, contact_name, contact_phone,
                         delivery_address, zone_id=None, lat=None, lng=None, tip="0.00", notes=""):
    if not items:
        raise ValidationError("Your cart is empty.")

    restaurant = Restaurant.objects.filter(slug=restaurant_slug,
                                           status=Restaurant.Status.ACTIVE).first()
    if not restaurant:
        raise ValidationError("Restaurant is not available.")
    if not restaurant.is_currently_open(timezone.localtime()):
        raise ValidationError("This restaurant is currently closed.")

    zone = _resolve_zone(restaurant, zone_id, lat, lng)

    subtotal = Decimal("0.00")
    built = []
    for line in items:
        item_id = line.get("item_id")
        qty = int(line.get("quantity", 0))
        if not item_id or qty <= 0:
            raise ValidationError("Each cart line needs an item and a positive quantity.")
        item = FoodItem.objects.filter(id=item_id, restaurant=restaurant,
                                       is_available=True).first()
        if not item:
            raise ValidationError("One of the items is no longer available.")
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
        raise ValidationError(
            f"Minimum order is BDT {restaurant.min_order_amount}. Add more items.")

    delivery_fee = _delivery_fee(restaurant, zone)
    tip_amount = Decimal(str(tip or "0.00"))
    total = subtotal + delivery_fee + tip_amount

    order = FoodOrder.objects.create(
        customer=customer if getattr(customer, "is_authenticated", False) else None,
        guest_name=contact_name, guest_phone=contact_phone, delivery_address=delivery_address,
        restaurant=restaurant, zone=zone, subtotal=subtotal, delivery_fee=delivery_fee,
        tip=tip_amount, total=total, notes=notes or "",
        eta_minutes=restaurant.avg_prep_minutes + DELIVERY_BUFFER_MINUTES,
    )
    for item, qty, unit, opts, line_total in built:
        FoodOrderItem.objects.create(order=order, item=item, item_name=item.name,
                                     unit_price=unit, quantity=qty, selected_options=opts,
                                     line_total=line_total)
    return order
