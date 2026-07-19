"""Admin restaurant onboarding — create a restaurant, optionally with an owner login,
zone assignments, and opening hours, in one atomic operation.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError

from food.models import Restaurant, RestaurantZone, RestaurantHours, DeliveryZone

User = get_user_model()


def _unique_restaurant_slug(name):
    base = slugify(name) or "restaurant"
    slug = base
    i = 2
    while Restaurant.objects.filter(slug=slug).exists():
        slug = f"{base}-{i}"
        i += 1
    return slug


def _create_owner(od):
    username, email, password = od.get("username"), od.get("email"), od.get("password")
    if not username or not email or not password:
        raise ValidationError("Owner requires username, email and password.")
    if User.objects.filter(email=email).exists():
        raise ValidationError("A user with that email already exists.")
    if User.objects.filter(username=username).exists():
        raise ValidationError("A user with that username already exists.")
    return User.objects.create_user(
        username=username, email=email, password=password,
        phone=od.get("phone", ""), role="Restaurant", country="Bangladesh",
    )


@transaction.atomic
def create_restaurant_with_owner(data):
    name = (data.get("name") or "").strip()
    if not name:
        raise ValidationError("Restaurant name is required.")

    owner = None
    od = data.get("owner")
    if od and (od.get("username") or od.get("email") or od.get("password")):
        owner = _create_owner(od)

    restaurant = Restaurant.objects.create(
        name=name, slug=_unique_restaurant_slug(name), owner=owner,
        name_bn=data.get("name_bn", ""), description=data.get("description", ""),
        phone=data.get("phone", ""), address=data.get("address", ""),
        cuisine_type=data.get("cuisine_type", ""),
        logo=data.get("logo", ""), cover_image=data.get("cover_image", ""),
        commission_percentage=data.get("commission_percentage") or Decimal("15.00"),
        base_delivery_fee=data.get("base_delivery_fee") or Decimal("0.00"),
        min_order_amount=data.get("min_order_amount") or Decimal("0.00"),
        avg_prep_minutes=data.get("avg_prep_minutes") or 30,
    )

    for zid in data.get("zone_ids", []) or []:
        zone = DeliveryZone.objects.filter(id=zid).first()
        if zone:
            RestaurantZone.objects.get_or_create(restaurant=restaurant, zone=zone)

    replace_hours(restaurant, data.get("hours", []) or [])
    return restaurant


def replace_hours(restaurant, hours):
    RestaurantHours.objects.filter(restaurant=restaurant).delete()
    for h in hours:
        RestaurantHours.objects.create(
            restaurant=restaurant, weekday=h["weekday"],
            open_time=h["open_time"], close_time=h["close_time"],
            is_closed=h.get("is_closed", False),
        )
