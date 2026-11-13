import json
import re

from catalog.models import Products, ProductVariant
from django.test import TestCase


class StoreDocumentTests(TestCase):
    def setUp(self):
        self.product = Products.objects.create(
            name="Cotton shirt",
            slug="cotton-shirt",
            description="<p>Comfortable cotton.</p>",
            sku="T1",
            initial_buying_price=100,
            initial_selling_price=200,
            image=["https://example.com/shirt.webp"],
        )
        ProductVariant.objects.create(
            product=self.product, sku="T1-M", size="M", price=200, stock_quantity=3
        )

    def test_product_response_is_crawlable_before_javascript(self):
        response = self.client.get("/api/store/documents/product/cotton-shirt/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("<h1>Cotton shirt</h1>", html)
        self.assertIn("https://www.fabrything.com/product/cotton-shirt", html)
        self.assertIn("Comfortable cotton.", html)
        schema = json.loads(
            re.search(r'type="application/ld\+json">(.*?)</script>', html).group(1)
        )
        self.assertEqual(schema["@graph"][0]["offers"][0]["price"], "200.00")
        self.assertEqual(html.count('rel="canonical"'), 1)

    def test_inactive_or_unknown_product_returns_real_404(self):
        self.product.status = "INACTIVE"
        self.product.save()
        self.assertEqual(
            self.client.get("/api/store/documents/product/cotton-shirt/").status_code,
            404,
        )
        self.assertEqual(
            self.client.get("/api/store/documents/product/missing/").status_code, 404
        )

    def test_home_and_shop_have_real_product_links(self):
        for path in ("home", "shop"):
            response = self.client.get("/api/store/documents/" + path + "/")
            self.assertEqual(response.status_code, 200)
            self.assertIn('href="/product/cotton-shirt"', response.content.decode())

    def test_invalid_page_returns_404_and_filters_are_noindex(self):
        self.assertEqual(
            self.client.get("/api/store/documents/shop/?page=oops").status_code, 404
        )
        self.assertEqual(
            self.client.get("/api/store/documents/shop/?page=9999").status_code, 404
        )
        response = self.client.get("/api/store/documents/shop/?q=cotton")
        self.assertIn("noindex,follow", response.content.decode())

    def test_source_text_cannot_escape_schema_or_html(self):
        self.product.description = '</script><script>alert("xss")</script>'
        self.product.save()
        response = self.client.get("/api/store/documents/product/cotton-shirt/")
        self.assertNotIn('<script>alert("xss")', response.content.decode())

    def test_home_tracking_queries_keep_the_home_canonical(self):
        response = self.client.get(
            "/api/store/documents/home/?page=2&utm_source=facebook"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'rel="canonical" href="https://www.fabrything.com/"',
            response.content.decode(),
        )
        self.assertNotIn("noindex,follow", response.content.decode())
