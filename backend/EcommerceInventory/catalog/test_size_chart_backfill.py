from django.test import TestCase

from accounts.models import Users
from catalog.models import Categories, Products
from catalog.services_size_chart_backfill import backfill_fabrilife_size_charts

RAW_CHART = (
    '[{"title":"Size chart - In inches (Expected Deviation < 3%)",'
    '"unit_of_measurement":"inch","chart":{'
    '"M":{"chest (round)":"36","length":"30","sleeve":"21"},'
    '"L":{"chest (round)":"38","length":"31","sleeve":"21"}}}]'
)


def _algolia_response(hits):
    return {"hits": hits}


class SizeChartBackfillTests(TestCase):
    def setUp(self):
        owner = Users.objects.create_user(username="r", email="r@x.com", password="x",
                                           role="Super Admin", country="Bangladesh")
        cat = Categories.objects.create(name="Tops", slug="women-tops", description="")
        self.owner = owner
        self.cat = cat
        self.chart_product = Products.objects.create(
            name="Womens Premium Tops - Estrella", slug="womens-premium-tops-estrella",
            sku="FS-9001", category_id=cat, description="", brand="Fabrilife",
            available_sizes=["M", "L", "XL"],
            initial_buying_price=1, initial_selling_price=1190,
            domain_user_id=owner, added_by_user_id=owner,
        )

    def test_exact_title_match_writes_size_chart(self):
        def fetcher(name):
            self.assertEqual(name, self.chart_product.name)
            return _algolia_response([
                {"title": "Womens Premium Tops - Estrella", "size_chart": RAW_CHART},
            ])

        results = backfill_fabrilife_size_charts(fetcher=fetcher, dry_run=False)
        self.chart_product.refresh_from_db()
        self.assertEqual(
            self.chart_product.size_chart,
            {"M": {"chest": 36.0, "length": 30.0, "sleeve": 21.0},
             "L": {"chest": 38.0, "length": 31.0, "sleeve": 21.0}},
        )
        self.assertEqual(results[0]["status"], "updated")

    def test_dry_run_writes_nothing(self):
        def fetcher(name):
            return _algolia_response([
                {"title": "Womens Premium Tops - Estrella", "size_chart": RAW_CHART},
            ])

        results = backfill_fabrilife_size_charts(fetcher=fetcher, dry_run=True)
        self.chart_product.refresh_from_db()
        self.assertEqual(self.chart_product.size_chart, {})
        self.assertEqual(results[0]["status"], "would_update")
        self.assertTrue(results[0]["size_chart"])  # reported, just not written

    def test_inexact_title_is_not_a_match(self):
        # A hit for a DIFFERENT, similarly-named product must never be
        # written onto this one -- that would be a wrong chart on a live page.
        def fetcher(name):
            return _algolia_response([
                {"title": "Womens Premium Tops - Estrella V2", "size_chart": RAW_CHART},
            ])

        results = backfill_fabrilife_size_charts(fetcher=fetcher, dry_run=False)
        self.chart_product.refresh_from_db()
        self.assertEqual(self.chart_product.size_chart, {})
        self.assertEqual(results[0]["status"], "no_match")

    def test_matched_product_with_no_chart_is_reported_not_written(self):
        def fetcher(name):
            return _algolia_response([
                {"title": "Womens Premium Tops - Estrella", "size_chart": None},
            ])

        results = backfill_fabrilife_size_charts(fetcher=fetcher, dry_run=False)
        self.chart_product.refresh_from_db()
        self.assertEqual(self.chart_product.size_chart, {})
        self.assertEqual(results[0]["status"], "no_chart")

    def test_fetch_error_is_reported_and_run_continues(self):
        def fetcher(name):
            raise RuntimeError("network down")

        results = backfill_fabrilife_size_charts(fetcher=fetcher, dry_run=False)
        self.assertEqual(results[0]["status"], "error")

    def test_products_without_sizes_are_not_candidates(self):
        Products.objects.create(
            name="Fabrilife Gift Card", slug="fabrilife-gift-card", sku="FS-9002",
            category_id=self.cat, description="", brand="Fabrilife",
            available_sizes=[], initial_buying_price=1, initial_selling_price=500,
            domain_user_id=self.owner, added_by_user_id=self.owner,
        )
        results = backfill_fabrilife_size_charts(fetcher=lambda name: _algolia_response([]))
        self.assertEqual(len(results), 1)  # only self.chart_product
        self.assertEqual(results[0]["name"], self.chart_product.name)

    def test_product_that_already_has_a_chart_is_not_a_candidate(self):
        self.chart_product.size_chart = {"M": {"chest": 36.0}}
        self.chart_product.save(update_fields=["size_chart"])
        results = backfill_fabrilife_size_charts(fetcher=lambda name: _algolia_response([]))
        self.assertEqual(results, [])

    def test_non_fabrilife_products_are_not_candidates(self):
        Products.objects.create(
            name="Some Laptop", slug="some-laptop", sku="FS-9003",
            category_id=self.cat, description="", brand="Dell",
            available_sizes=["13-inch"], initial_buying_price=1, initial_selling_price=50000,
            domain_user_id=self.owner, added_by_user_id=self.owner,
        )
        results = backfill_fabrilife_size_charts(fetcher=lambda name: _algolia_response([]))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], self.chart_product.name)
