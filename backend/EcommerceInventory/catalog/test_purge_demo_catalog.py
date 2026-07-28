"""
BUG 4: purge the dummy demo catalog (~60 loremflickr-placeholder products
from seed_bd_store) now that real products are live, without touching real
products, order history, or the TAXONOMY categories that stay intentionally
empty (Phones/Gadgets have no real products yet).
"""
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from accounts.models import Users
from catalog.models import Categories, Products, ProductVariant
from orders.models import Order, OrderItem


def run_purge(*args):
    out = StringIO()
    call_command("purge_demo_catalog", *args, stdout=out)
    return out.getvalue()


class PurgeDemoCatalogTests(TestCase):
    def setUp(self):
        self.owner = Users.objects.create_user(
            username="owner3", email="owner3@x.com", password="x",
            role="Super Admin", country="Bangladesh")

        # A demo top-level category from seed_bd_store.CATEGORIES (not part of
        # the TAXONOMY tree) that will end up completely empty after purge.
        self.demo_only_category = Categories.objects.create(
            name="Watches", slug="watches", description="d",
            domain_user_id=self.owner, added_by_user_id=self.owner)
        self.demo_product = Products.objects.create(
            name="Fastrack Analog Blue Dial", slug="fastrack-analog-blue-dial",
            description="d", sku="FT-5033",
            initial_buying_price=2000, initial_selling_price=2990,
            image=["https://loremflickr.com/600/800/wristwatch?lock=1234"],
            category_id=self.demo_only_category,
            domain_user_id=self.owner, added_by_user_id=self.owner, status="ACTIVE",
        )

        # A demo category that ALSO holds a real product -- must survive.
        self.mixed_category = Categories.objects.create(
            name="Shoes", slug="shoes", description="d",
            domain_user_id=self.owner, added_by_user_id=self.owner)
        self.demo_product_in_mixed = Products.objects.create(
            name="Bay Street Sneakers", slug="bay-street-sneakers",
            description="d", sku="FT-5011",
            initial_buying_price=2000, initial_selling_price=2990,
            image=["https://loremflickr.com/600/800/sneakers?lock=5678"],
            category_id=self.mixed_category,
            domain_user_id=self.owner, added_by_user_id=self.owner, status="ACTIVE",
        )
        self.real_product = Products.objects.create(
            name="Fabrilife Classic Tee", slug="fabrilife-classic-tee",
            description="d", sku="FAB-1001",
            initial_buying_price=300, initial_selling_price=590,
            image=["/api/media/realhash1234/"],
            category_id=self.mixed_category,
            domain_user_id=self.owner, added_by_user_id=self.owner, status="ACTIVE",
        )

        # An empty TAXONOMY category (Phones has no real products yet) -- must
        # survive purge even though it has no products and no children.
        self.taxonomy_category = Categories.objects.create(
            name="Phones", slug="phones", description="d",
            domain_user_id=self.owner, added_by_user_id=self.owner)

    def test_dry_run_deletes_nothing(self):
        output = run_purge()
        self.assertTrue(Products.objects.filter(pk=self.demo_product.pk).exists())
        self.assertTrue(Categories.objects.filter(pk=self.demo_only_category.pk).exists())
        self.assertIn("Dry run", output)

    def test_apply_deletes_loremflickr_product(self):
        run_purge("--apply")
        self.assertFalse(Products.objects.filter(pk=self.demo_product.pk).exists())

    def test_apply_leaves_real_product_untouched(self):
        run_purge("--apply")
        self.assertTrue(Products.objects.filter(pk=self.real_product.pk).exists())

    def test_apply_skips_loremflickr_product_referenced_by_an_order(self):
        variant = ProductVariant.objects.create(
            product=self.demo_product, sku="FT-5033-OS", price=Decimal("2990"),
            stock_quantity=5,
        )
        order = Order.objects.create(
            subtotal=Decimal("2990"), shipping_amount=Decimal("60"),
            total_amount=Decimal("3050"), contact_name="Karim", contact_phone="017",
            shipping_address={"address": "x"},
        )
        OrderItem.objects.create(
            order=order, variant=variant, product_name=self.demo_product.name,
            sku=variant.sku, unit_price=Decimal("2990"), quantity=1,
            line_total=Decimal("2990"),
        )

        output = run_purge("--apply")

        self.assertTrue(Products.objects.filter(pk=self.demo_product.pk).exists())
        self.assertIn("skip", output.lower())
        self.assertIn(self.demo_product.sku, output)

    def test_apply_removes_emptied_demo_category(self):
        run_purge("--apply")
        self.assertFalse(Categories.objects.filter(slug="watches").exists())

    def test_apply_keeps_demo_category_holding_a_real_product(self):
        run_purge("--apply")
        self.assertTrue(Categories.objects.filter(slug="shoes").exists())

    def test_apply_keeps_empty_taxonomy_category(self):
        run_purge("--apply")
        self.assertTrue(Categories.objects.filter(slug="phones").exists(),
                        "an empty TAXONOMY category must survive purge")
