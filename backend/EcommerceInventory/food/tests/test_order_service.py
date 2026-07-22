from decimal import Decimal
from django.test import TestCase
from rest_framework.exceptions import ValidationError
from food.models import (Restaurant, RestaurantHours, DeliveryZone, RestaurantZone,
                         FoodCategory, FoodItem, FoodItemOptionGroup, FoodItemOption)
from food.services import place_food_cod_order


def open_all_week(restaurant):
    for wd in range(7):
        RestaurantHours.objects.create(restaurant=restaurant, weekday=wd,
                                       open_time="00:00", close_time="23:59")


class PlaceFoodOrderTests(TestCase):
    def setUp(self):
        self.zone = DeliveryZone.objects.create(name="Zone1", center_lat="23.8",
                                                center_lng="90.4", radius_km="5")
        self.r = Restaurant.objects.create(name="R", slug="r", status=Restaurant.Status.ACTIVE,
                                           is_open=True, base_delivery_fee=Decimal("30.00"),
                                           min_order_amount=Decimal("100.00"), avg_prep_minutes=25)
        RestaurantZone.objects.create(restaurant=self.r, zone=self.zone)
        open_all_week(self.r)
        self.cat = FoodCategory.objects.create(restaurant=self.r, name="Main")
        self.item = FoodItem.objects.create(restaurant=self.r, category_id=self.cat,
                                            name="Biriyani", slug="biriyani", price=Decimal("120.00"))
        self.grp = FoodItemOptionGroup.objects.create(item=self.item, name="Size", max_select=1)
        self.opt = FoodItemOption.objects.create(group=self.grp, name="Large", price_delta=Decimal("50.00"))

    def _lines(self, qty=1, options=None):
        return [{"item_id": self.item.id, "quantity": qty, "option_ids": options or []}]

    def test_totals_are_computed_server_side(self):
        order = place_food_cod_order(customer=None, restaurant_slug="r",
                                     items=self._lines(qty=1, options=[self.opt.id]),
                                     contact_name="A", contact_phone="017", delivery_address="addr",
                                     zone_id=self.zone.id, tip="10.00")
        # subtotal = (120 + 50) * 1 = 170; fee = 30; tip = 10; total = 210
        self.assertEqual(order.subtotal, Decimal("170.00"))
        self.assertEqual(order.delivery_fee, Decimal("30.00"))
        self.assertEqual(order.total, Decimal("210.00"))
        self.assertEqual(order.eta_minutes, 25 + 20)
        self.assertEqual(order.items.count(), 1)

    def test_below_min_order_rejected(self):
        self.r.min_order_amount = Decimal("500.00"); self.r.save()
        with self.assertRaises(ValidationError):
            place_food_cod_order(customer=None, restaurant_slug="r", items=self._lines(),
                                 contact_name="A", contact_phone="017",
                                 delivery_address="a", zone_id=self.zone.id)

    def test_closed_restaurant_rejected(self):
        self.r.is_open = False; self.r.save()
        with self.assertRaises(ValidationError):
            place_food_cod_order(customer=None, restaurant_slug="r", items=self._lines(qty=2),
                                 contact_name="A", contact_phone="017",
                                 delivery_address="a", zone_id=self.zone.id)

    def test_non_serviceable_zone_rejected(self):
        other = DeliveryZone.objects.create(name="Z2", center_lat="10", center_lng="10", radius_km="1")
        with self.assertRaises(ValidationError):
            place_food_cod_order(customer=None, restaurant_slug="r", items=self._lines(qty=2),
                                 contact_name="A", contact_phone="017",
                                 delivery_address="a", zone_id=other.id)

    def test_restaurant_with_no_zones_delivers_everywhere(self):
        """No RestaurantZone rows means "not configured yet", not "delivers nowhere".

        A freshly onboarded restaurant used to reject every checkout with an opaque
        400 until an admin remembered to tick its zones. Assigning even one zone
        switches it back to an explicit allow-list (the test below).
        """
        RestaurantZone.objects.filter(restaurant=self.r).delete()
        other = DeliveryZone.objects.create(name="Z2", center_lat="10", center_lng="10", radius_km="1")
        order = place_food_cod_order(customer=None, restaurant_slug="r", items=self._lines(qty=2),
                                     contact_name="A", contact_phone="017",
                                     delivery_address="a", zone_id=other.id)
        self.assertEqual(order.zone_id, other.id)
        # No per-zone row, so the fee falls back to the restaurant's base fee.
        self.assertEqual(order.delivery_fee, Decimal("30.00"))

    def test_inactive_zone_still_rejected_when_unconfigured(self):
        """The everywhere fallback covers *active* zones only."""
        RestaurantZone.objects.filter(restaurant=self.r).delete()
        dead = DeliveryZone.objects.create(name="Z3", center_lat="10", center_lng="10",
                                           radius_km="1", is_active=False)
        with self.assertRaises(ValidationError):
            place_food_cod_order(customer=None, restaurant_slug="r", items=self._lines(qty=2),
                                 contact_name="A", contact_phone="017",
                                 delivery_address="a", zone_id=dead.id)

    def test_unavailable_item_rejected(self):
        self.item.is_available = False; self.item.save()
        with self.assertRaises(ValidationError):
            place_food_cod_order(customer=None, restaurant_slug="r", items=self._lines(qty=2),
                                 contact_name="A", contact_phone="017",
                                 delivery_address="a", zone_id=self.zone.id)

    def test_invalid_option_rejected(self):
        other_item = FoodItem.objects.create(restaurant=self.r, category_id=self.cat,
                                             name="Other", slug="other", price=Decimal("50.00"))
        other_grp = FoodItemOptionGroup.objects.create(item=other_item, name="X")
        foreign_opt = FoodItemOption.objects.create(group=other_grp, name="Nope")
        with self.assertRaises(ValidationError):
            place_food_cod_order(customer=None, restaurant_slug="r",
                                 items=self._lines(qty=2, options=[foreign_opt.id]),
                                 contact_name="A", contact_phone="017",
                                 delivery_address="a", zone_id=self.zone.id)

    def test_zone_resolved_from_latlng_when_no_zone_id(self):
        order = place_food_cod_order(customer=None, restaurant_slug="r", items=self._lines(qty=2),
                                     contact_name="A", contact_phone="017", delivery_address="a",
                                     lat="23.80", lng="90.40")
        self.assertEqual(order.zone_id, self.zone.id)
