"""The platform markup rule: max(floor, base_price * percentage%), the same
shape as food.pricing.commission_for -- see catalog/pricing.py."""
from decimal import Decimal

from django.test import TestCase

from core.models import StoreConfiguration
from catalog.pricing import apply_markup, markup_for


class MarkupRuleTests(TestCase):
    """Defaults: floor=50, percentage=3% (StoreConfiguration.get_solo())."""

    def test_the_floor_carries_a_cheap_item(self):
        # 3% of 99 is ~2.97 -- far below a floor worth having. The floor
        # must win here or a 99 BDT item earns the platform almost nothing.
        self.assertEqual(markup_for(Decimal("99")), Decimal("50.00"))
        self.assertEqual(apply_markup(Decimal("99")), 149.0)

    def test_the_percentage_takes_over_on_an_expensive_item(self):
        # 3% of 989,900 is 29,697 -- far above the floor.
        self.assertEqual(markup_for(Decimal("989900")), Decimal("29697.00"))
        self.assertEqual(apply_markup(Decimal("989900")), 1019597.0)

    def test_the_median_product_earns_the_documented_margin(self):
        # The report's worked example: 3% of 3,200 is 96, comfortably above
        # the 50 BDT floor.
        self.assertEqual(markup_for(Decimal("3200")), Decimal("96.00"))
        self.assertEqual(apply_markup(Decimal("3200")), 3296.0)

    def test_a_none_base_price_has_no_markup(self):
        self.assertIsNone(markup_for(None))
        self.assertIsNone(apply_markup(None))

    def test_custom_floor_and_percentage_override_the_config(self):
        self.assertEqual(apply_markup(Decimal("1000"), floor=Decimal("10"), percentage=Decimal("50")),
                        1500.0)

    def test_applying_markup_twice_to_the_same_base_is_idempotent(self):
        # The whole point: calling apply_markup repeatedly on the SAME
        # base_price must always return the same number.
        first = apply_markup(Decimal("3200"))
        second = apply_markup(Decimal("3200"))
        self.assertEqual(first, second)

    def test_applying_markup_to_an_already_marked_up_price_would_double_it(self):
        # This is the failure mode the whole design guards against: proof
        # that apply_markup must only ever be called on base_price, never on
        # a selling price that already has a markup baked in.
        base = Decimal("3200")
        once = apply_markup(base)
        twice = apply_markup(Decimal(str(once)))
        self.assertNotEqual(once, twice)
        self.assertGreater(twice, once)


class MarkupConfigTests(TestCase):
    """The singleton config lives on StoreConfiguration (core.models) --
    picked over a new model because platform markup is a store-wide setting
    like the fixed shipping rate, not a per-order snapshot the way
    food.models.DeliveryPricing is."""

    def test_defaults(self):
        cfg = StoreConfiguration.get_solo()
        self.assertEqual(cfg.markup_percentage, Decimal("3.00"))
        self.assertEqual(cfg.markup_floor, Decimal("50.00"))

    def test_a_custom_config_is_honoured(self):
        cfg = StoreConfiguration.get_solo()
        cfg.markup_percentage = Decimal("10.00")
        cfg.markup_floor = Decimal("20.00")
        cfg.save()
        self.assertEqual(apply_markup(Decimal("1000"), config=cfg), 1100.0)

    def test_negative_percentage_is_clamped_to_zero(self):
        cfg = StoreConfiguration.get_solo()
        cfg.markup_percentage = Decimal("-5.00")
        cfg.save()
        cfg.refresh_from_db()
        self.assertEqual(cfg.markup_percentage, Decimal("0.00"))

    def test_a_mistyped_over_100_percent_is_clamped(self):
        # A mis-typed 500% must not silently 6x every price on the site.
        cfg = StoreConfiguration.get_solo()
        cfg.markup_percentage = Decimal("500.00")
        cfg.save()
        cfg.refresh_from_db()
        self.assertEqual(cfg.markup_percentage, Decimal("100.00"))

    def test_a_negative_floor_is_clamped_to_zero(self):
        cfg = StoreConfiguration.get_solo()
        cfg.markup_floor = Decimal("-10.00")
        cfg.save()
        cfg.refresh_from_db()
        self.assertEqual(cfg.markup_floor, Decimal("0.00"))
