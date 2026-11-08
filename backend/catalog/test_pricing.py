"""The platform markup rule: max(floor, base_price * percentage%), the same
shape as food.pricing.commission_for -- see catalog/pricing.py."""
from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from core.models import StoreConfiguration
from catalog.pricing import apply_markup, attractive_price, markup_for, quote_supplier_price


class AttractivePriceTests(SimpleTestCase):
    def test_examples_boundaries_and_half_up_ties(self):
        for raw, expected in [
            ('26', 25), ('69', 70), ('800', 799), ('273', 270),
            ('2137', 2099), ('22.5', 25), ('65', 70), ('850', 899),
            ('49.99', 50), ('50', 50), ('499.99', 500), ('500', 499),
            ('849.999', 799), ('0.01', 5), ('0', 0),
        ]:
            with self.subTest(raw=raw):
                result = attractive_price(raw)
                self.assertIsInstance(result, Decimal)
                self.assertEqual(result, Decimal(expected))

    def test_missing_invalid_and_nonfinite_prices(self):
        self.assertIsNone(attractive_price(None))
        for raw in ['-1', 'NaN', 'Infinity', '-Infinity', 'bad']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                attractive_price(raw)

    def test_foreign_currency_keeps_cents(self):
        for currency in ['USD', 'EUR', 'GBP']:
            with self.subTest(currency=currency):
                self.assertEqual(attractive_price('2137.45', currency=currency), Decimal('2137.45'))

    def test_explicit_revenue_minimum_moves_up_to_attractive_price(self):
        for minimum, expected in [('48', 50), ('66', 70), ('500', 599), ('1420.46', 1499)]:
            with self.subTest(minimum=minimum):
                self.assertEqual(attractive_price(minimum, minimum=Decimal(minimum)), Decimal(expected))


class MarkupRuleTests(TestCase):
    """Defaults: floor=50, percentage=3% (StoreConfiguration.get_solo())."""

    def test_the_floor_carries_a_cheap_item(self):
        # 3% of 99 is ~2.97 -- far below a floor worth having. The floor
        # must win here or a 99 BDT item earns the platform almost nothing.
        self.assertEqual(markup_for(Decimal("99")), Decimal("50.00"))
        self.assertEqual(apply_markup(Decimal("99")), 149)

    def test_the_percentage_takes_over_on_an_expensive_item(self):
        # 3% of 989,900 is 29,697 -- far above the floor.
        self.assertEqual(markup_for(Decimal("989900")), Decimal("29697.00"))
        self.assertEqual(apply_markup(Decimal("989900")), 1019597)

    def test_the_median_product_earns_the_documented_margin(self):
        # The report's worked example: 3% of 3,200 is 96, comfortably above
        # the 50 BDT floor.
        self.assertEqual(markup_for(Decimal("3200")), Decimal("96.00"))
        self.assertEqual(apply_markup(Decimal("3200")), 3296)

    def test_a_none_base_price_has_no_markup(self):
        self.assertIsNone(markup_for(None))
        self.assertIsNone(apply_markup(None))

    def test_custom_floor_and_percentage_override_the_config(self):
        self.assertEqual(apply_markup(Decimal("1000"), floor=Decimal("10"), percentage=Decimal("50")),
                        1499)

    def test_rounding_is_applied_after_markup(self):
        self.assertEqual(apply_markup('750', floor='50', percentage='0'), Decimal('800'))
        self.assertIsInstance(apply_markup('750'), Decimal)

    def test_configured_floor_survives_attractive_rounding(self):
        for cost in ('449', '450', '750', '1290', '1349', '1350'):
            with self.subTest(cost=cost):
                selling = apply_markup(cost)
                self.assertLessEqual(selling, Decimal(cost) + markup_for(cost))
                self.assertGreaterEqual(selling - Decimal(cost), Decimal('50'))
        self.assertEqual(apply_markup('1290'), Decimal('1340'))
        self.assertEqual(quote_supplier_price('1290', {})['selling_price'], Decimal('1340'))

    def test_foreign_store_currency_preserves_fractional_markup(self):
        cfg = StoreConfiguration.get_solo()
        cfg.currency = 'USD'
        self.assertEqual(apply_markup('26.25', floor='0', percentage='3', config=cfg), Decimal('27.04'))

    def test_supplier_quotes_are_decimal_and_round_converted_bdt(self):
        from django.utils import timezone
        quote = quote_supplier_price('10', {
            'source_currency': 'USD', 'fx_rate_to_bdt': '120',
            'fx_rate_observed_at': timezone.now().isoformat(),
            'fee_percent': '2', 'target_margin_percent': '10',
            'shipping_base_bdt': '50',
        })
        self.assertIsInstance(quote['base_price'], Decimal)
        self.assertIsInstance(quote['selling_price'], Decimal)
        self.assertEqual(quote['selling_price'], Decimal('1499'))
        self.assertGreaterEqual(quote['selling_price'] * Decimal('.88') -
                                quote['base_price'] - quote['shipping_cost'], Decimal('50'))

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
        self.assertEqual(apply_markup(Decimal("1000"), config=cfg), 1099)

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
