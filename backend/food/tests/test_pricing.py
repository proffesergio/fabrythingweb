"""The two money rules: commission = max(floor, %), and delivery never loses money."""
from decimal import Decimal

from django.test import TestCase
from rest_framework.exceptions import ValidationError

from food.models import DeliveryPricing, DeliveryZone, Restaurant, RestaurantZone, Village
from food.pricing import commission_for, delivery_quote, distance_for

# Bancharampur-ish. 0.01 degrees of latitude is ~1.11 km, which makes the
# distances in these tests easy to reason about.
LAT, LNG = Decimal("23.770000"), Decimal("90.780000")


def at_km_north(km):
    """A point roughly `km` north of the restaurant."""
    return LAT + Decimal(str(round(km / 111.0, 6))), LNG


class CommissionTests(TestCase):
    def setUp(self):
        self.r = Restaurant.objects.create(
            name="R", slug="r", status=Restaurant.Status.ACTIVE,
            commission_percentage=Decimal("12.00"), min_commission_amount=Decimal("25.00"))

    def test_the_floor_carries_a_small_order(self):
        # 12% of ৳150 is ৳18 — less than a rider costs. This is the case a pure
        # percentage model loses money on, and it is the common rural basket.
        self.assertEqual(commission_for(self.r, Decimal("150.00")), Decimal("25.00"))

    def test_the_percentage_takes_over_on_a_large_order(self):
        self.assertEqual(commission_for(self.r, Decimal("600.00")), Decimal("72.00"))

    def test_the_crossover_is_where_the_two_meet(self):
        # 12% of 208.33 ≈ 25. Just above it, the percentage wins.
        self.assertEqual(commission_for(self.r, Decimal("210.00")), Decimal("25.20"))

    def test_commission_never_exceeds_the_food_itself(self):
        """A ৳20 order must not bill the restaurant ৳25 for the privilege of
        selling something — that would make restaurant_payout negative."""
        self.assertEqual(commission_for(self.r, Decimal("20.00")), Decimal("20.00"))

    def test_a_zero_order_costs_nothing(self):
        self.assertEqual(commission_for(self.r, Decimal("0.00")), Decimal("0.00"))

    def test_rates_are_per_restaurant(self):
        vip = Restaurant.objects.create(name="V", slug="v", commission_percentage=Decimal("5.00"),
                                        min_commission_amount=Decimal("0.00"))
        self.assertEqual(commission_for(vip, Decimal("150.00")), Decimal("7.50"))


class DeliveryQuoteTests(TestCase):
    def setUp(self):
        self.cfg = DeliveryPricing.get_solo()
        self.zone = DeliveryZone.objects.create(name="Z", center_lat=LAT, center_lng=LNG,
                                                radius_km=Decimal("15"))
        self.r = Restaurant.objects.create(name="R", slug="r", status=Restaurant.Status.ACTIVE,
                                           pickup_lat=LAT, pickup_lng=LNG,
                                           base_delivery_fee=Decimal("30.00"))

    def quote(self, km=None, **kw):
        lat, lng = at_km_north(km) if km is not None else (None, None)
        return delivery_quote(self.r, zone=self.zone, lat=lat, lng=lng, **kw)

    def test_inside_the_free_radius_costs_the_base_fee(self):
        q = self.quote(1.0)
        self.assertEqual(q["fee"], Decimal("30.00"))
        self.assertEqual(q["priced_by"], "distance")

    def test_beyond_the_free_radius_the_fee_grows_with_distance(self):
        near, far = self.quote(2.0)["fee"], self.quote(6.0)["fee"]
        self.assertGreater(far, near)
        # 30 + 12 * (6-2) = 78 → rounded up to the next ৳5 = 80
        self.assertEqual(far, Decimal("80.00"))

    def test_fees_are_round_numbers_for_a_cash_economy(self):
        for km in [2.5, 3.3, 4.1, 5.7, 7.2]:
            fee = self.quote(km)["fee"]
            self.assertEqual(fee % Decimal("5"), Decimal("0"), f"{km}km → {fee}")

    def test_rounding_goes_up_never_down(self):
        # Rounding a customer-facing fee down is the platform paying for change.
        q = self.quote(2.1)   # 30 + 12*0.1 = 31.2
        self.assertEqual(q["fee"], Decimal("35.00"))

    def test_the_fee_is_capped(self):
        self.cfg.max_fee = Decimal("60.00")
        self.cfg.save()
        self.assertEqual(self.quote(9.0, config=self.cfg)["fee"], Decimal("60.00"))

    def test_beyond_range_is_refused_rather_than_quoted(self):
        """An honest refusal beats a delivery nobody is paid properly for."""
        with self.assertRaises(ValidationError) as ctx:
            self.quote(20.0)
        self.assertIn("delivery range", str(ctx.exception))

    def test_a_preview_can_ask_for_the_out_of_range_price_anyway(self):
        q = self.quote(20.0, enforce_range=False)
        self.assertGreater(q["fee"], Decimal("0"))


class MarginGuaranteeTests(TestCase):
    """The platform must never pay out more delivery money than it took in.

    platform_revenue = commission + delivery_fee - rider_base_pay, so a rider
    paid more than the fee turns delivery into a subsidy out of commission.
    """

    def setUp(self):
        self.cfg = DeliveryPricing.get_solo()
        self.zone = DeliveryZone.objects.create(name="Z", center_lat=LAT, center_lng=LNG,
                                                radius_km=Decimal("15"))
        self.r = Restaurant.objects.create(name="R", slug="r", status=Restaurant.Status.ACTIVE,
                                           pickup_lat=LAT, pickup_lng=LNG,
                                           base_delivery_fee=Decimal("30.00"))

    def _quote(self, km, **kw):
        lat, lng = at_km_north(km)
        return delivery_quote(self.r, zone=self.zone, lat=lat, lng=lng, config=self.cfg, **kw)

    def test_margin_is_positive_at_every_distance_with_default_rates(self):
        for km in [0.5, 1, 2, 3, 5, 8, 11.5]:
            q = self._quote(km)
            self.assertGreaterEqual(q["platform_margin"], self.cfg.platform_min_margin,
                                    f"{km} km: fee {q['fee']} vs rider {q['rider_base_pay']}")

    def test_a_longer_delivery_earns_MORE_not_less(self):
        """per_km_fee > rider_per_km is what makes distance profitable. If this
        ever inverts, long deliveries quietly eat the commission."""
        margins = [self._quote(km)["platform_margin"] for km in [2, 4, 6, 8, 10]]
        self.assertEqual(margins, sorted(margins))
        self.assertGreater(margins[-1], margins[0])

    def test_a_misconfigured_rate_costs_the_platform_nothing(self):
        """The guarantee is structural, not a consequence of choosing good rates:
        an owner who sets rider pay above the fee in the admin panel caps the
        rider, they do not create a loss."""
        self.cfg.rider_per_km = Decimal("999.00")
        self.cfg.rider_base_pay = Decimal("999.00")
        self.cfg.save()
        for km in [1, 5, 10]:
            q = self._quote(km)
            self.assertGreaterEqual(q["platform_margin"], Decimal("0"))
            self.assertEqual(q["platform_margin"], self.cfg.platform_min_margin)

    def test_rider_pay_is_never_negative(self):
        self.cfg.platform_min_margin = Decimal("9999.00")
        self.cfg.save()
        self.assertEqual(self._quote(3)["rider_base_pay"], Decimal("0.00"))


class FallbackTests(TestCase):
    """What happens when we cannot measure the distance."""

    def setUp(self):
        self.zone = DeliveryZone.objects.create(name="Z", center_lat=LAT, center_lng=LNG,
                                                radius_km=Decimal("15"))
        self.r = Restaurant.objects.create(name="R", slug="r", status=Restaurant.Status.ACTIVE,
                                           base_delivery_fee=Decimal("40.00"))

    def test_a_restaurant_with_no_pickup_pin_falls_back_to_the_flat_fee(self):
        q = delivery_quote(self.r, zone=self.zone, lat=LAT, lng=LNG)
        self.assertEqual(q["fee"], Decimal("40.00"))
        self.assertEqual(q["priced_by"], "flat")
        self.assertIsNone(q["distance_km"])
        self.assertEqual(q["distance_source"], "no-pickup-pin")

    def test_the_flat_fallback_still_protects_the_margin(self):
        self.r.base_delivery_fee = Decimal("10.00")   # less than rider base pay
        q = delivery_quote(self.r, zone=self.zone)
        self.assertGreaterEqual(q["fee"] - q["rider_base_pay"], Decimal("0"))

    def test_no_pin_uses_the_village_centre_when_it_has_one(self):
        self.r.pickup_lat, self.r.pickup_lng = LAT, LNG
        self.r.save()
        vlat, vlng = at_km_north(4.0)
        village = Village.objects.create(zone=self.zone, name="Far", center_lat=vlat, center_lng=vlng)
        q = delivery_quote(self.r, zone=self.zone, village=village)
        self.assertEqual(q["distance_source"], "village")
        self.assertAlmostEqual(float(q["distance_km"]), 4.0, delta=0.15)

    def test_no_pin_and_no_village_centre_falls_back_to_the_zone_centre(self):
        self.r.pickup_lat, self.r.pickup_lng = at_km_north(3.0)
        self.r.save()
        village = Village.objects.create(zone=self.zone, name="Unmapped")
        q = delivery_quote(self.r, zone=self.zone, village=village)
        self.assertEqual(q["distance_source"], "zone")
        self.assertAlmostEqual(float(q["distance_km"]), 3.0, delta=0.15)

    def test_a_dropped_pin_beats_every_fallback(self):
        self.r.pickup_lat, self.r.pickup_lng = LAT, LNG
        self.r.save()
        village = Village.objects.create(zone=self.zone, name="V",
                                         center_lat=at_km_north(9)[0], center_lng=LNG)
        plat, plng = at_km_north(1.0)
        q = delivery_quote(self.r, zone=self.zone, village=village, lat=plat, lng=plng)
        self.assertEqual(q["distance_source"], "pin")
        self.assertAlmostEqual(float(q["distance_km"]), 1.0, delta=0.15)


class ZoneOverrideTests(TestCase):
    def setUp(self):
        self.zone = DeliveryZone.objects.create(name="Z", center_lat=LAT, center_lng=LNG,
                                                radius_km=Decimal("15"))
        self.r = Restaurant.objects.create(name="R", slug="r", status=Restaurant.Status.ACTIVE,
                                           pickup_lat=LAT, pickup_lng=LNG,
                                           base_delivery_fee=Decimal("30.00"))

    def test_an_explicit_zone_price_outranks_the_distance_formula(self):
        """A per-zone fee is a deliberate commercial decision (a promo rate) and
        must not be silently overwritten by the distance calculation."""
        RestaurantZone.objects.create(restaurant=self.r, zone=self.zone,
                                      delivery_fee=Decimal("20.00"))
        lat, lng = at_km_north(6.0)
        q = delivery_quote(self.r, zone=self.zone, lat=lat, lng=lng)
        self.assertEqual(q["fee"], Decimal("20.00"))
        self.assertEqual(q["priced_by"], "zone-override")

    def test_an_underpriced_override_caps_the_rider_not_the_platform(self):
        RestaurantZone.objects.create(restaurant=self.r, zone=self.zone,
                                      delivery_fee=Decimal("20.00"))
        lat, lng = at_km_north(6.0)
        q = delivery_quote(self.r, zone=self.zone, lat=lat, lng=lng)
        self.assertGreaterEqual(q["platform_margin"], Decimal("5.00"))
        self.assertEqual(q["rider_base_pay"], Decimal("15.00"))

    def test_a_zero_fee_promo_zone_is_honoured(self):
        RestaurantZone.objects.create(restaurant=self.r, zone=self.zone,
                                      delivery_fee=Decimal("0.00"))
        q = delivery_quote(self.r, zone=self.zone, lat=LAT, lng=LNG)
        self.assertEqual(q["fee"], Decimal("0.00"))
        self.assertEqual(q["rider_base_pay"], Decimal("0.00"))


class DistanceTests(TestCase):
    def test_distance_is_none_without_a_pickup_pin(self):
        r = Restaurant.objects.create(name="R", slug="r")
        km, source = distance_for(r, lat=LAT, lng=LNG)
        self.assertIsNone(km)
        self.assertEqual(source, "no-pickup-pin")

    def test_distance_matches_the_haversine_the_frontend_uses(self):
        r = Restaurant.objects.create(name="R", slug="r", pickup_lat=LAT, pickup_lng=LNG)
        lat, lng = at_km_north(5.0)
        km, source = distance_for(r, lat=lat, lng=lng)
        self.assertEqual(source, "pin")
        self.assertAlmostEqual(float(km), 5.0, delta=0.1)


class DeliveryQuoteEndpointTests(TestCase):
    """GET api/food/delivery-quote/ — what checkout shows before you commit."""

    def setUp(self):
        from rest_framework.test import APIClient
        self.client = APIClient()
        self.zone = DeliveryZone.objects.create(name="Z", center_lat=LAT, center_lng=LNG,
                                                radius_km=Decimal("15"))
        self.r = Restaurant.objects.create(name="R", slug="r", status=Restaurant.Status.ACTIVE,
                                           pickup_lat=LAT, pickup_lng=LNG,
                                           base_delivery_fee=Decimal("30.00"), avg_prep_minutes=25)

    def _get(self, **params):
        params.setdefault("restaurant", "r")
        return self.client.get("/api/food/delivery-quote/", params).json()["data"]

    def test_quotes_a_distance_priced_fee(self):
        lat, lng = at_km_north(6.0)
        d = self._get(zone=self.zone.id, lat=str(lat), lng=str(lng))
        self.assertTrue(d["deliverable"])
        self.assertEqual(d["fee"], "80.00")
        self.assertEqual(d["priced_by"], "distance")
        self.assertEqual(d["distance_source"], "pin")

    def test_the_quote_matches_what_the_order_actually_charges(self):
        """The quote and the charge come from one function on purpose — a
        dropdown that offers what the order endpoint rejects is the exact bug
        this project has already shipped once."""
        lat, lng = at_km_north(4.0)
        quoted = self._get(zone=self.zone.id, lat=str(lat), lng=str(lng))["fee"]
        charged = delivery_quote(self.r, zone=self.zone, lat=lat, lng=lng)["fee"]
        self.assertEqual(Decimal(quoted), charged)

    def test_out_of_range_answers_200_with_a_reason_not_an_error(self):
        # The customer is asking a question, not placing an order; the UI has to
        # be able to explain the refusal, and callApi discards non-2xx bodies.
        lat, lng = at_km_north(30.0)
        d = self._get(zone=self.zone.id, lat=str(lat), lng=str(lng))
        self.assertFalse(d["deliverable"])
        self.assertIn("delivery range", d["reason"])

    def test_an_unserved_zone_is_refused_with_a_reason(self):
        other = DeliveryZone.objects.create(name="Other", center_lat="10", center_lng="10",
                                            radius_km=Decimal("2"))
        RestaurantZone.objects.create(restaurant=self.r, zone=self.zone)   # explicit allow-list
        d = self._get(zone=other.id)
        self.assertFalse(d["deliverable"])
        self.assertIn("does not deliver", d["reason"])

    def test_a_village_implies_its_zone(self):
        vlat, vlng = at_km_north(5.0)
        v = Village.objects.create(zone=self.zone, name="V", center_lat=vlat, center_lng=vlng)
        d = self._get(village=v.id)
        self.assertTrue(d["deliverable"])
        self.assertEqual(d["distance_source"], "village")

    def test_unknown_restaurant_is_404(self):
        res = self.client.get("/api/food/delivery-quote/", {"restaurant": "nope"})
        self.assertEqual(res.status_code, 404)

    def test_the_quote_needs_no_login(self):
        d = self._get(zone=self.zone.id)
        self.assertTrue(d["deliverable"])


class OrderSnapshotTests(TestCase):
    """Placing an order freezes the distance and the rider's pay onto it."""

    def setUp(self):
        from rest_framework.test import APIClient
        from datetime import time
        from django.utils import timezone
        from food.models import FoodCategory, FoodItem, RestaurantHours
        self.client = APIClient()
        self.zone = DeliveryZone.objects.create(name="Z", center_lat=LAT, center_lng=LNG,
                                                radius_km=Decimal("20"))
        self.r = Restaurant.objects.create(name="R", slug="r", status=Restaurant.Status.ACTIVE,
                                           pickup_lat=LAT, pickup_lng=LNG,
                                           base_delivery_fee=Decimal("30.00"))
        RestaurantHours.objects.create(restaurant=self.r, weekday=timezone.localtime().weekday(),
                                       open_time=time(0, 0), close_time=time(23, 59))
        cat = FoodCategory.objects.create(restaurant=self.r, name="C")
        self.item = FoodItem.objects.create(restaurant=self.r, category_id=cat, name="Dish",
                                            slug="dish", price=Decimal("300.00"), is_available=True)

    def _place(self, lat, lng):
        return self.client.post("/api/food/orders/", {
            "restaurant_slug": "r", "contact_name": "A", "contact_phone": "017",
            "delivery_address": "here", "zone_id": self.zone.id,
            "delivery_lat": str(lat), "delivery_lng": str(lng),
            "items": [{"item_id": self.item.id, "quantity": 1, "option_ids": []}],
        }, format="json")

    def test_a_placed_order_records_the_distance_it_was_priced_at(self):
        from food.models import FoodOrder
        lat, lng = at_km_north(6.0)
        res = self._place(lat, lng)
        self.assertEqual(res.status_code, 201, res.content)
        order = FoodOrder.objects.get(order_code=res.json()["data"]["order_code"])
        self.assertAlmostEqual(float(order.distance_km), 6.0, delta=0.15)
        self.assertEqual(order.delivery_fee, Decimal("80.00"))
        self.assertGreater(order.rider_base_pay, Decimal("0"))
        # The platform is up on the delivery leg before commission is counted.
        self.assertGreater(order.delivery_fee - order.rider_base_pay, Decimal("0"))

    def test_a_nearby_order_pays_the_base_fee(self):
        from food.models import FoodOrder
        lat, lng = at_km_north(1.0)
        order = FoodOrder.objects.get(order_code=self._place(lat, lng).json()["data"]["order_code"])
        self.assertEqual(order.delivery_fee, Decimal("30.00"))

    def test_an_address_beyond_range_is_refused_at_checkout(self):
        lat, lng = at_km_north(18.0)
        res = self._place(lat, lng)
        self.assertEqual(res.status_code, 400)
        self.assertIn("delivery range", str(res.content))

    def test_the_total_includes_the_distance_priced_fee(self):
        lat, lng = at_km_north(6.0)
        d = self._place(lat, lng).json()["data"]
        self.assertEqual(Decimal(d["total"]), Decimal("380.00"))   # 300 food + 80 delivery

    def test_a_pin_inside_a_chosen_zone_still_prices_by_the_pin(self):
        """The zone decides *whether* we deliver; the pin decides *what it
        costs*. Checkout sends both, and the charge must match the quote it
        showed — pricing off the zone centre instead would silently charge a
        different fee than the screen said."""
        from food.models import FoodOrder
        lat, lng = at_km_north(6.0)
        quoted = self.client.get("/api/food/delivery-quote/", {
            "restaurant": "r", "zone": self.zone.id, "lat": str(lat), "lng": str(lng),
        }).json()["data"]
        order = FoodOrder.objects.get(order_code=self._place(lat, lng).json()["data"]["order_code"])
        self.assertEqual(Decimal(quoted["fee"]), order.delivery_fee)
        self.assertEqual(quoted["distance_source"], "pin")
