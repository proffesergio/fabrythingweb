from pathlib import Path

from django.test import SimpleTestCase

import json

from catalog.scrape_parsers import (
    parse_bdt_price,
    parse_fabrilife_algolia_size_chart,
    parse_fabrilife_listing,
    parse_fabrilife_product,
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


class CanvasitProductTests(SimpleTestCase):
    """Fixture is a trimmed, real capture of
    https://canvasit.com.bd/apple-macbook-air-m5-13-inch-512gb (fetched
    2026-07-28). canvasit.com.bd is OpenCart like potakait.com but runs a
    different theme -- plain ``<h1>`` instead of ``h1.product_title``,
    ``.price-wrapper .price-group`` instead of ``.special``/``.price``,
    ``.product-manufacturer`` instead of ``.product-wid-info``, a
    ``.swiper-slide`` image carousel instead of ``#gallery``, and a two-``td``
    specification table instead of ``td.name``/``td.value``. Assertions pin
    the exact values on that live page, same rigor as OpenCartProductTests --
    selector drift on the real site must fail loudly rather than silently
    returning empty/garbage data (this is exactly how the original
    potakait-only selectors silently returned 0 products for every canvasit
    category)."""

    def setUp(self):
        self.html = (FIXTURES / "canvasit_product.html").read_text(encoding="utf-8")
        self.product = parse_opencart_product(self.html)

    def test_extracts_core_fields(self):
        p = self.product
        self.assertTrue(p["name"])
        self.assertIsInstance(p["price"], float)
        self.assertGreater(p["price"], 0)
        self.assertIsInstance(p["images"], list)
        self.assertTrue(p["images"])
        self.assertTrue(all(u.startswith("http") for u in p["images"]))
        self.assertIsInstance(p["specifications"], dict)

    def test_exact_name(self):
        self.assertEqual(self.product["name"], "Apple MacBook Air M5 Chip 13-inch 512GB")

    def test_discount_price_when_both_old_and_new_present(self):
        # The captured page shows .product-price-new=165,000 (current, what
        # you pay) and .product-price-old=181,000 (crossed-out original):
        # price is the higher original, discount_price is the lower current
        # price -- same convention as OpenCartProductTests (potakait).
        self.assertEqual(self.product["price"], 181000.0)
        self.assertEqual(self.product["discount_price"], 165000.0)

    def test_brand(self):
        self.assertEqual(self.product["brand"], "Apple")

    def test_images_are_absolute_and_deduped(self):
        self.assertEqual(
            self.product["images"],
            [
                "https://canvasit.com.bd/image/cache/catalog/Laptop/MackBook/"
                "Apple-MacBook-Air-M5-Chip-13-inch-512GB-2-550x550.jpg",
                "https://canvasit.com.bd/image/cache/catalog/Laptop/MackBook/"
                "Apple-MacBook-Air-M5-Chip-13-inch-1TB-(10-core-CPU,-10-core-GPU)-550x550.jpg",
                "https://canvasit.com.bd/image/cache/catalog/Laptop/MackBook/"
                "macbook-air-15-m4-sky-blue-01-550x550.jpg",
            ],
        )

    def test_specifications_has_known_keys(self):
        specs = self.product["specifications"]
        self.assertEqual(specs["Battery capacity"], "53.8 w")
        self.assertEqual(specs["Fingerprint Sensor"], "Touch ID")
        # Section header rows (colspan=2, no value cell) must not leak in as
        # bogus entries.
        self.assertNotIn("Battery Info:", specs)
        self.assertNotIn("Basic Information", specs)

    def test_description_mentions_product(self):
        self.assertIn("Apple MacBook Air M5 Chip 13-inch", self.product["description"])


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

    def test_extracts_product_urls_canvasit_theme(self):
        # canvasit.com.bd wraps each card in .product-layout > .product-thumb
        # (no .product-item at all). Both selectors match the same card, so
        # the URL must appear exactly once, in document order.
        html = """
        <div class="product-layout">
            <div class="product-thumb">
                <div class="image">
                    <a href="/orico-pfb-a23-foldable-laptop-stand" class="product-img">
                        <img src="/image/1.jpg">
                    </a>
                </div>
                <div class="caption">
                    <div class="name"><a href="/orico-pfb-a23-foldable-laptop-stand">Orico stand</a></div>
                </div>
            </div>
        </div>
        <div class="product-layout">
            <div class="product-thumb">
                <div class="image">
                    <a href="/apple-macbook-air-m5" class="product-img">
                        <img src="/image/2.jpg">
                    </a>
                </div>
                <div class="caption">
                    <div class="name"><a href="/apple-macbook-air-m5">MacBook Air M5</a></div>
                </div>
            </div>
        </div>
        """
        urls = parse_opencart_listing(html, "https://canvasit.com.bd/laptop")
        self.assertEqual(
            urls,
            [
                "https://canvasit.com.bd/orico-pfb-a23-foldable-laptop-stand",
                "https://canvasit.com.bd/apple-macbook-air-m5",
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


class FabrilifeProductTests(SimpleTestCase):
    """Fixture is a trimmed, real capture of
    https://fabrilife.com/product/72899-premium-jacquard-panjabi-sabri
    (fetched 2026-07-28). Assertions pin the exact values on that live page,
    same rigor as OpenCartProductTests -- selector drift on the real site
    must fail loudly rather than silently returning empty/garbage data."""

    def setUp(self):
        self.html = (FIXTURES / "fabrilife_product.html").read_text(encoding="utf-8")
        self.product = parse_fabrilife_product(self.html)

    def test_extracts_core_fields(self):
        p = self.product
        self.assertTrue(p["name"])
        self.assertIsInstance(p["price"], float)
        self.assertGreater(p["price"], 0)
        self.assertIsInstance(p["images"], list)
        self.assertTrue(p["images"])
        self.assertTrue(all(u.startswith("http") for u in p["images"]))
        self.assertIsInstance(p["specifications"], dict)
        self.assertIn(p["gender"], {"MEN", "WOMEN", "KIDS"})
        self.assertIsInstance(p["sizes"], list)
        self.assertTrue(p["sizes"])

    def test_exact_name(self):
        self.assertEqual(self.product["name"], "Premium Jacquard Panjabi - Sabri")

    def test_discount_price_when_both_old_and_new_present(self):
        # The captured page shows price-old/regular_price_field=2800 (crossed
        # out original) and price-now/price_field=2150 (current, what you
        # pay): price is the higher original, discount_price the lower
        # current price -- same convention as parse_opencart_product.
        self.assertEqual(self.product["price"], 2800.0)
        self.assertEqual(self.product["discount_price"], 2150.0)

    def test_brand(self):
        self.assertEqual(self.product["brand"], "Fabrilife")

    def test_gender(self):
        self.assertEqual(self.product["gender"], "MEN")

    def test_sizes_exact(self):
        self.assertEqual(self.product["sizes"], ["44", "46"])

    def test_material_from_fabric_type_label(self):
        self.assertEqual(self.product["material"], "Jacquard Dobby Cotton")

    def test_images_are_absolute_and_deduped(self):
        self.assertEqual(
            self.product["images"],
            [
                "https://fabrilife.com/products/65f7d75521889-square.jpg",
                "https://fabrilife.com/products/65f7d75561e23-square.jpg",
                "https://fabrilife.com/image-gallery/65f7d7555c656-square.jpg",
            ],
        )

    def test_specifications_has_known_keys(self):
        specs = self.product["specifications"]
        self.assertEqual(specs["Weave"], "Plain weave")
        self.assertEqual(specs["Durability"], "Durable and long-lasting")
        self.assertEqual(specs["Type"], "Regular Fit")

    def test_description_mentions_product(self):
        self.assertIn("Jacquard Dobby Cotton", self.product["description"])

    def test_no_size_chart_on_this_product(self):
        # This Panjabi page has no "Size chart" block at all -- most
        # Fabrilife products besides Tops/Kurti don't carry measurements.
        # Must come back as {} (falsy), not raise or return garbage, so the
        # storefront's "hide when no data" rule has something to check.
        self.assertEqual(self.product["size_chart"], {})


class FabrilifeSizeChartTests(SimpleTestCase):
    """Fixture is a trimmed, real capture of
    https://fabrilife.com/product/74169-womens-premium-tops-estrella
    (fetched 2026-07-29), captured specifically because it has a "Size
    chart - In inches (Expected Deviation < 3%)" table with INCH/CM tabs --
    same rigor as FabrilifeProductTests: pin the exact values on the live
    page so selector drift fails loudly."""

    def setUp(self):
        html = (FIXTURES / "fabrilife_product_size_chart.html").read_text(encoding="utf-8")
        self.product = parse_fabrilife_product(html)

    def test_size_chart_exact(self):
        self.assertEqual(
            self.product["size_chart"],
            {
                "M": {"chest": 36.0, "length": 30.0, "sleeve": 21.0},
                "L": {"chest": 38.0, "length": 31.0, "sleeve": 21.0},
                "XL": {"chest": 40.0, "length": 32.0, "sleeve": 21.5},
                "2XL": {"chest": 42.0, "length": 33.0, "sleeve": 22.0},
            },
        )

    def test_only_inch_tab_is_read_not_cm(self):
        # The CM tab-pane on the same page has chest=91.4 for M -- if the
        # parser ever picked the wrong pane this would silently start
        # returning centimeters mislabeled as inches.
        self.assertEqual(self.product["size_chart"]["M"]["chest"], 36.0)

    def test_other_fields_still_parse_alongside_the_chart(self):
        # The size-chart tab-content div re-uses the `.self-product-description`
        # class the real description block also uses -- guard against the
        # chart section leaking into the description/specifications extraction.
        self.assertEqual(self.product["name"], "Womens Premium Tops - Estrella")
        self.assertIn("Estrella Premium Top", self.product["description"])
        self.assertNotIn("Size chart", self.product["description"])


class FabrilifeAlgoliaSizeChartTests(SimpleTestCase):
    """`raw` here is the exact `size_chart` field shape confirmed live
    (2026-07-29) on an Algolia `products` search hit for "Womens Premium
    Tops - Estrella" -- catalog.services_size_chart_backfill reads this
    field directly off a search hit instead of re-fetching/parsing the
    product page HTML."""

    RAW = (
        '[{"title":"Size chart - In inches (Expected Deviation < 3%)",'
        '"unit_of_measurement":"inch","chart":{'
        '"M":{"chest (round)":"36","length":"30","sleeve":"21"},'
        '"L":{"chest (round)":"38","length":"31","sleeve":"21"},'
        '"XL":{"chest (round)":"40","length":"32","sleeve":"21.5"},'
        '"2XL":{"chest (round)":"42","length":"33","sleeve":"22"}}}]'
    )

    def test_parses_json_string(self):
        self.assertEqual(
            parse_fabrilife_algolia_size_chart(self.RAW),
            {
                "M": {"chest": 36.0, "length": 30.0, "sleeve": 21.0},
                "L": {"chest": 38.0, "length": 31.0, "sleeve": 21.0},
                "XL": {"chest": 40.0, "length": 32.0, "sleeve": 21.5},
                "2XL": {"chest": 42.0, "length": 33.0, "sleeve": 22.0},
            },
        )

    def test_accepts_already_decoded_list(self):
        import json
        self.assertEqual(
            parse_fabrilife_algolia_size_chart(json.loads(self.RAW)),
            parse_fabrilife_algolia_size_chart(self.RAW),
        )

    def test_missing_field_is_empty(self):
        self.assertEqual(parse_fabrilife_algolia_size_chart(None), {})
        self.assertEqual(parse_fabrilife_algolia_size_chart(""), {})

    def test_malformed_json_is_empty_not_raise(self):
        self.assertEqual(parse_fabrilife_algolia_size_chart("not json"), {})

    def test_no_inch_entry_is_empty(self):
        raw = '[{"title":"x","unit_of_measurement":"cm","chart":{"M":{"chest":"91.4"}}}]'
        self.assertEqual(parse_fabrilife_algolia_size_chart(raw), {})


class FabrilifeSpecEdgeCaseTests(SimpleTestCase):
    """Synthetic markup covering shapes the captured fixture alone doesn't
    exercise: a label heading with no following value (must not leak into
    specifications as an empty entry), and a material value followed by
    marketing copy after an en dash (must be trimmed at the dash, mirroring
    the real "Fabric Type: 95% Cotton + 5% Lylon -- Soft, breathable..."
    copy seen on fabrilife.com kurti pages)."""

    def _product(self, description_html):
        html = f"""
        <html><head><meta property="og:url" content="https://fabrilife.com/product/1-x"></head>
        <body>
        <div class="product-title-row"><h4 class="tiny-margin">Test Product</h4></div>
        <div class="price-area"><div class="price-now">TK <span class="price_field">500</span></div></div>
        <div class="size-picker-block"><div class="size-selector">M</div></div>
        <div class="self-product-description">{description_html}</div>
        <script>var g4a = {{"item_category":"Mens"}};</script>
        </body></html>
        """
        return parse_fabrilife_product(html)

    def test_empty_label_not_stored(self):
        p = self._product("<p><strong>Product Specification:</strong></p><p><strong>Fabric Type:</strong> Cotton</p>")
        self.assertNotIn("Product Specification", p["specifications"])
        self.assertEqual(p["specifications"]["Fabric Type"], "Cotton")

    def test_material_trimmed_at_dash(self):
        p = self._product(
            "<p><strong>Fabric Type:</strong> 95% Cotton + 5% Lylon – Soft, breathable, and durable</p>"
        )
        self.assertEqual(p["material"], "95% Cotton + 5% Lylon")

    def test_material_empty_when_not_stated(self):
        p = self._product("<p>Made with fine quality fabric, no explicit label here.</p>")
        self.assertEqual(p["material"], "")


class FabrilifeListingTests(SimpleTestCase):
    """``html`` here is the raw JSON body of an Algolia ``query`` response
    against fabrilife.com's own ``products`` index -- see the module-level
    comment in scrape_parsers.py for why the faceted /shop URL's raw HTML
    can't be used instead."""

    def test_extracts_product_urls_from_hits(self):
        body = json.dumps({
            "hits": [
                {"id": 72899, "slug": "premium-jacquard-panjabi-sabri", "title": "A"},
                {"id": 73105, "slug": "womens-premium-kurti-empress-pink", "title": "B"},
            ]
        })
        urls = parse_fabrilife_listing(body, "https://fabrilife.com/")
        self.assertEqual(
            urls,
            [
                "https://fabrilife.com/product/72899-premium-jacquard-panjabi-sabri",
                "https://fabrilife.com/product/73105-womens-premium-kurti-empress-pink",
            ],
        )

    def test_dedupes_and_skips_hits_missing_id_or_slug(self):
        body = json.dumps({
            "hits": [
                {"id": 1, "slug": "a"},
                {"id": 1, "slug": "a"},
                {"id": 2, "slug": ""},
                {"slug": "no-id"},
                {"id": 3},
            ]
        })
        urls = parse_fabrilife_listing(body, "https://fabrilife.com/")
        self.assertEqual(urls, ["https://fabrilife.com/product/1-a"])

    def test_malformed_json_returns_empty_list(self):
        self.assertEqual(parse_fabrilife_listing("not json", "https://fabrilife.com/"), [])
