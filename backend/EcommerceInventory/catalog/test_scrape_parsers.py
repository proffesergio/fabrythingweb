from pathlib import Path

from django.test import SimpleTestCase

from catalog.scrape_parsers import (
    parse_bdt_price,
    parse_opencart_listing,
    parse_opencart_product,
)

FIXTURES = Path(__file__).resolve().parent / "test_fixtures"


class BdtPriceTests(SimpleTestCase):
    def test_plain(self):
        self.assertEqual(parse_bdt_price("8,500৳"), 8500.0)

    def test_symbol_first_and_spaces(self):
        self.assertEqual(parse_bdt_price("৳ 12,990"), 12990.0)

    def test_garbage_returns_none(self):
        self.assertIsNone(parse_bdt_price("Out of stock"))

    def test_empty_returns_none(self):
        self.assertIsNone(parse_bdt_price(""))
        self.assertIsNone(parse_bdt_price(None))


class OpenCartProductTests(SimpleTestCase):
    """Fixture is a trimmed, real capture of
    https://potakait.com/thermalright-peerless-assassin-120-digital-argb-black-cpu-cooler
    (fetched 2026-07-28). Assertions pin the exact values on that live page
    so selector drift on the real site fails loudly rather than silently
    returning empty/garbage data."""

    def setUp(self):
        self.html = (FIXTURES / "opencart_product.html").read_text(encoding="utf-8")
        self.product = parse_opencart_product(self.html)

    def test_extracts_core_fields(self):
        p = self.product
        self.assertTrue(p["name"])
        self.assertIsInstance(p["price"], float)
        self.assertGreater(p["price"], 0)
        self.assertIsInstance(p["images"], list)
        self.assertTrue(all(u.startswith("http") for u in p["images"]))
        self.assertIsInstance(p["specifications"], dict)

    def test_exact_name(self):
        self.assertEqual(
            self.product["name"],
            "Thermalright Peerless Assassin 120 Digital ARGB BLACK CPU Cooler",
        )

    def test_discount_price_when_both_old_and_new_present(self):
        # The captured page shows span.special=5,800৳ (current) and
        # span.price=6,500৳ (crossed-out original): price is the higher
        # original, discount_price is the lower current price.
        self.assertEqual(self.product["price"], 6500.0)
        self.assertEqual(self.product["discount_price"], 5800.0)

    def test_brand(self):
        self.assertEqual(self.product["brand"], "Thermalright")

    def test_images_are_absolute_and_deduped(self):
        images = self.product["images"]
        # 3 distinct thumbnails; the main-image preview duplicates the first
        # thumbnail and must be deduped away.
        self.assertEqual(
            images,
            [
                "https://potakait.com/image/cache/catalog/cooler/thermalright/"
                "peerless-assassin-120-digital-argb-black-cpu-cooler/"
                "thermalright-peerless-assassin-120-digital-argb-black-cpu-cooler-1-400x400.png",
                "https://potakait.com/image/cache/catalog/cooler/thermalright/"
                "peerless-assassin-120-digital-argb-black-cpu-cooler/"
                "thermalright-peerless-assassin-120-digital-argb-black-cpu-cooler-2-400x400.png",
                "https://potakait.com/image/cache/catalog/cooler/thermalright/"
                "peerless-assassin-120-digital-argb-black-cpu-cooler/"
                "thermalright-peerless-assassin-120-digital-argb-black-cpu-cooler-400x400.png",
            ],
        )

    def test_specifications_has_known_keys(self):
        specs = self.product["specifications"]
        self.assertEqual(specs["Intel"], "LGA115X/1200/1700/1851")
        self.assertEqual(specs["AMD"], "AM4/AM5")
        self.assertEqual(specs["Warranty"], "3 Years")
        # Section header rows (colspan=3, no value cell) must not leak in as
        # bogus entries.
        self.assertNotIn("Supported Sockets", specs)
        self.assertNotIn("Key Features", specs)

    def test_description_mentions_product(self):
        self.assertIn("Thermalright Peerless Assassin", self.product["description"])


class OpenCartListingTests(SimpleTestCase):
    def test_extracts_product_urls(self):
        html = """
        <div class="row main-content categories-products">
            <div class="col-lg-3">
                <div class="product-item extra">
                    <a href="/msi-titan-18-hx-gaming-laptop">
                        <div class="product-img"><img src="/image/1.jpg"></div>
                    </a>
                </div>
            </div>
            <div class="col-lg-3">
                <div class="product-item extra">
                    <a href="/hp-omnibook-5-laptop">
                        <div class="product-img"><img src="/image/2.jpg"></div>
                    </a>
                </div>
            </div>
        </div>
        <table class="recent-product-price-table">
            <tr><td class="product-item-name"><a href="/some-other-listing-only-link">Not a card</a></td></tr>
        </table>
        """
        urls = parse_opencart_listing(html, "https://potakait.com/all-laptops")
        self.assertEqual(
            urls,
            [
                "https://potakait.com/msi-titan-18-hx-gaming-laptop",
                "https://potakait.com/hp-omnibook-5-laptop",
            ],
        )

    def test_dedupes_preserving_order(self):
        html = """
        <div class="product-item extra"><a href="/a">A</a></div>
        <div class="product-item extra"><a href="/b">B</a></div>
        <div class="product-item extra"><a href="/a">A again</a></div>
        """
        urls = parse_opencart_listing(html, "https://potakait.com/")
        self.assertEqual(urls, ["https://potakait.com/a", "https://potakait.com/b"])
