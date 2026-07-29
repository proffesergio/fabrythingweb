"""StoreConfiguration.shipping_for -- the single place per-product shipping
is resolved into an order-level charge.

Rule (owner's choice): order shipping = max(the store's flat rate, every
distinct per-product shipping_fee in the cart). One delivery trip, so the
bulkiest/costliest item to ship sets the price; a product with no override
(None) never contributes to the max, and one that ships free (an explicit 0)
never pulls the order shipping *below* the store's flat rate on its own.
Free-shipping-threshold, when it applies, wins over all of this.
"""
from decimal import Decimal

from django.test import TestCase

from core.models import StoreConfiguration


class ShippingForBaselineTests(TestCase):
    """No product fees at all -- must behave exactly as before this feature."""

    def setUp(self):
        self.cfg = StoreConfiguration.get_solo()
        self.cfg.fixed_shipping_rate = Decimal("60.00")
        self.cfg.free_shipping_threshold = None
        self.cfg.save()

    def test_no_product_fees_uses_flat_rate(self):
        self.assertEqual(self.cfg.shipping_for(Decimal("500")), Decimal("60.00"))

    def test_two_products_neither_with_a_fee_uses_flat_rate(self):
        # Worked example 2: cart = two products, no per-product fees ->
        # shipping = flat rate, exactly as today.
        self.assertEqual(
            self.cfg.shipping_for(Decimal("500"), [None, None]), Decimal("60.00")
        )


class ShippingForMaxRuleTests(TestCase):
    def setUp(self):
        self.cfg = StoreConfiguration.get_solo()
        self.cfg.fixed_shipping_rate = Decimal("60.00")
        self.cfg.free_shipping_threshold = None
        self.cfg.save()

    def test_highest_per_product_fee_wins(self):
        # Worked example 1: a flat shirt (no fee) + a monitor with a 250 fee
        # -> shipping is 250, not 60 + 250 and not just the shirt's fallback.
        shipping = self.cfg.shipping_for(Decimal("2000"), [None, Decimal("250")])
        self.assertEqual(shipping, Decimal("250"))

    def test_fee_below_flat_rate_does_not_undercut_the_flat_rate(self):
        # Worked example 3: one product with a 30 fee, flat rate 60 -> 60,
        # because the flat rate is always in the candidate set as a floor.
        shipping = self.cfg.shipping_for(Decimal("500"), [Decimal("30")])
        self.assertEqual(shipping, Decimal("60.00"))

    def test_multiple_fees_take_the_max_not_the_sum(self):
        shipping = self.cfg.shipping_for(
            Decimal("5000"), [Decimal("100"), Decimal("250"), Decimal("40")]
        )
        self.assertEqual(shipping, Decimal("250"))

    def test_accepts_plain_floats_too(self):
        # Callers may pass floats (e.g. straight from a float DB column);
        # shipping_for must coerce rather than blow up on mixed types.
        shipping = self.cfg.shipping_for(Decimal("500"), [30.0, 250.0])
        self.assertEqual(shipping, Decimal("250"))


class ShippingForNullVsExplicitZeroTests(TestCase):
    """NULL ("use the store rate") must stay distinct from an explicit 0
    ("this product ships free") -- a `if fee:` truthy check would wrongly
    treat 0 the same as missing and silently drop it from the candidate set.
    """

    def setUp(self):
        self.cfg = StoreConfiguration.get_solo()
        self.cfg.fixed_shipping_rate = Decimal("60.00")
        self.cfg.free_shipping_threshold = None
        self.cfg.save()

    def test_null_fee_is_excluded_from_candidates_not_coerced_to_zero(self):
        # A None fee contributes nothing; with no other candidate the flat
        # rate alone determines shipping.
        shipping = self.cfg.shipping_for(Decimal("500"), [None])
        self.assertEqual(shipping, Decimal("60.00"))

    def test_explicit_zero_fee_is_a_real_candidate_not_dropped(self):
        # An explicit 0 must actually enter the max() as 0, distinctly from
        # being skipped like None -- provable when the flat rate is itself 0,
        # so nothing else is left to fall back on.
        self.cfg.fixed_shipping_rate = Decimal("0.00")
        self.cfg.save()
        shipping = self.cfg.shipping_for(Decimal("500"), [Decimal("0")])
        self.assertEqual(shipping, Decimal("0.00"))

    def test_explicit_zero_alongside_a_real_fee_does_not_win_the_max(self):
        shipping = self.cfg.shipping_for(Decimal("500"), [Decimal("0"), Decimal("120")])
        self.assertEqual(shipping, Decimal("120"))


class ShippingForFreeThresholdStillWinsTests(TestCase):
    """Free-shipping-threshold logic must still short-circuit everything
    above it, including a cart carrying a hefty per-product fee."""

    def setUp(self):
        self.cfg = StoreConfiguration.get_solo()
        self.cfg.fixed_shipping_rate = Decimal("60.00")
        self.cfg.free_shipping_threshold = Decimal("2000.00")
        self.cfg.save()

    def test_below_threshold_still_applies_flat_rate(self):
        self.assertEqual(self.cfg.shipping_for(Decimal("1000")), Decimal("60.00"))

    def test_at_or_above_threshold_is_free_with_no_product_fees(self):
        self.assertEqual(self.cfg.shipping_for(Decimal("2000")), Decimal("0.00"))

    def test_at_or_above_threshold_is_free_even_with_a_high_product_fee(self):
        # The threshold must win over the max() rule too -- a customer who
        # qualifies for free shipping should not be charged 250 anyway.
        shipping = self.cfg.shipping_for(Decimal("2500"), [Decimal("250")])
        self.assertEqual(shipping, Decimal("0.00"))

    def test_below_threshold_with_product_fee_uses_the_max_rule(self):
        shipping = self.cfg.shipping_for(Decimal("1000"), [Decimal("250")])
        self.assertEqual(shipping, Decimal("250"))
