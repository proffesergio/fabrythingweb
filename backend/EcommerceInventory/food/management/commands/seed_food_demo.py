"""Seed demo food restaurants, delivery zones, and menus (idempotent).

Runs safely on every deploy (via build.sh) so the customer Food app has real
restaurants + menus to show without needing shell access. Keyed by slug/name so
re-runs never duplicate.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from food.models import (
    DeliveryZone, Restaurant, RestaurantZone, RestaurantHours,
    FoodCategory, FoodItem, FoodItemOptionGroup, FoodItemOption,
)

ZONES = [
    {"name": "Central Bazar", "name_bn": "কেন্দ্রীয় বাজার", "lat": "24.3636", "lng": "88.6241", "radius": "7"},
    {"name": "University Area", "name_bn": "বিশ্ববিদ্যালয় এলাকা", "lat": "24.3745", "lng": "88.6380", "radius": "5"},
]

RESTAURANTS = [
    {
        "name": "Star Kitchen", "name_bn": "স্টার কিচেন", "slug": "star-kitchen",
        "cuisine": "Bengali", "fee": "40.00", "min": "100.00", "prep": 25,
        "categories": [
            {"name": "Rice & Biryani", "items": [
                {"name": "Chicken Biriyani", "price": "180.00", "options": [
                    {"group": "Size", "max": 1, "required": True, "opts": [("Regular", "0.00"), ("Large", "60.00")]},
                ]},
                {"name": "Beef Tehari", "price": "160.00"},
            ]},
            {"name": "Curries", "items": [
                {"name": "Chicken Curry", "price": "140.00"},
                {"name": "Dal", "price": "60.00", "veg": True},
            ]},
        ],
    },
    {
        "name": "Dhaka Fast Food", "name_bn": "ঢাকা ফাস্ট ফুড", "slug": "dhaka-fast-food",
        "cuisine": "Fast Food", "fee": "30.00", "min": "80.00", "prep": 20,
        "categories": [
            {"name": "Burgers", "items": [
                {"name": "Beef Burger", "price": "120.00", "options": [
                    {"group": "Add-ons", "max": 3, "required": False, "opts": [("Cheese", "20.00"), ("Extra Patty", "50.00")]},
                ]},
                {"name": "Chicken Burger", "price": "110.00"},
            ]},
            {"name": "Sides", "items": [
                {"name": "French Fries", "price": "70.00", "veg": True},
                {"name": "Cold Drink", "price": "40.00", "veg": True},
            ]},
        ],
    },
]


class Command(BaseCommand):
    help = "Seed demo food restaurants, zones, and menus (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        zones = []
        for z in ZONES:
            zone, _ = DeliveryZone.objects.get_or_create(
                name=z["name"],
                defaults={"name_bn": z["name_bn"], "center_lat": z["lat"],
                          "center_lng": z["lng"], "radius_km": z["radius"], "is_active": True},
            )
            zones.append(zone)

        for r in RESTAURANTS:
            rest, _ = Restaurant.objects.get_or_create(
                slug=r["slug"],
                defaults={"name": r["name"], "name_bn": r["name_bn"], "cuisine_type": r["cuisine"],
                          "status": Restaurant.Status.ACTIVE, "is_open": True,
                          "base_delivery_fee": Decimal(r["fee"]), "min_order_amount": Decimal(r["min"]),
                          "avg_prep_minutes": r["prep"]},
            )
            for zone in zones:
                RestaurantZone.objects.get_or_create(restaurant=rest, zone=zone)
            if not rest.hours.exists():
                for wd in range(7):
                    RestaurantHours.objects.create(restaurant=rest, weekday=wd,
                                                   open_time="09:00", close_time="23:00")
            for ci, c in enumerate(r["categories"]):
                cat, _ = FoodCategory.objects.get_or_create(
                    restaurant=rest, name=c["name"], defaults={"display_order": ci})
                for ii, it in enumerate(c["items"]):
                    item, created = FoodItem.objects.get_or_create(
                        restaurant=rest, slug=slugify(it["name"]),
                        defaults={"category_id": cat, "name": it["name"], "price": Decimal(it["price"]),
                                  "is_available": True, "is_veg": it.get("veg", False), "display_order": ii},
                    )
                    if created:
                        for g in it.get("options", []):
                            grp = FoodItemOptionGroup.objects.create(
                                item=item, name=g["group"], max_select=g["max"], is_required=g["required"])
                            for oi, (oname, odelta) in enumerate(g["opts"]):
                                FoodItemOption.objects.create(
                                    group=grp, name=oname, price_delta=Decimal(odelta), display_order=oi)

        self.stdout.write(self.style.SUCCESS(
            f"Food demo ready: {Restaurant.objects.count()} restaurants, "
            f"{FoodItem.objects.count()} items, {DeliveryZone.objects.count()} zones."))
