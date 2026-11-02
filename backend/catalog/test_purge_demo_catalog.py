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
from catalog.models import Categories, Products, ProductQuestions, ProductReviews, ProductVariant
from orders.models import Order, OrderItem
from storefront.models import Cart, CartItem


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

    def test_apply_skips_demo_product_sitting_in_a_live_customers_cart(self):
        """IMPORTANT 1: a live customer's CartItem cascades from
        ProductVariant -> Products (storefront/models.py:23-27,
        catalog/models.py:112-115), so the bulk Products.delete() used to
        cascade-delete real customers' cart line items with no report and no
        skip -- unlike the OrderItem path above. This must get the same
        treatment: skip by default, report why, and never delete silently."""
        customer = Users.objects.create_user(
            username="cust1", email="cust1@x.com", password="x",
            role="Customer", country="Bangladesh")
        variant = ProductVariant.objects.create(
            product=self.demo_product, sku="FT-5033-CART", price=Decimal("2990"),
            stock_quantity=5,
        )
        cart = Cart.objects.create(user=customer)
        cart_item = CartItem.objects.create(cart=cart, variant=variant, quantity=2)

        output = run_purge("--apply")

        self.assertTrue(
            Products.objects.filter(pk=self.demo_product.pk).exists(),
            "a demo product sitting in a live customer's cart must not be "
            "deleted by default -- it currently gets silently cascaded away")
        self.assertTrue(
            CartItem.objects.filter(pk=cart_item.pk).exists(),
            "the customer's cart item must survive a default (non-forced) purge run")
        self.assertIn("cart", output.lower())
        self.assertIn(self.demo_product.sku, output)

    def test_dry_run_reports_cart_items_before_any_delete_happens(self):
        """The dry run is the owner's only preview before an irreversible
        delete, so cart-item impact must be printed prominently -- not just
        discovered after --apply."""
        customer = Users.objects.create_user(
            username="cust2", email="cust2@x.com", password="x",
            role="Customer", country="Bangladesh")
        variant = ProductVariant.objects.create(
            product=self.demo_product, sku="FT-5033-CART2", price=Decimal("2990"),
            stock_quantity=5,
        )
        cart = Cart.objects.create(user=customer)
        CartItem.objects.create(cart=cart, variant=variant, quantity=1)

        output = run_purge()

        self.assertIn("cart", output.lower())
        self.assertIn(self.demo_product.name, output)
        self.assertTrue(Products.objects.filter(pk=self.demo_product.pk).exists())

    def test_force_cart_deletes_product_and_cascades_the_cart_item(self):
        """--force-cart is the explicit, deliberate override -- the owner has
        seen the dry-run report and chooses to proceed anyway."""
        customer = Users.objects.create_user(
            username="cust3", email="cust3@x.com", password="x",
            role="Customer", country="Bangladesh")
        variant = ProductVariant.objects.create(
            product=self.demo_product, sku="FT-5033-CART3", price=Decimal("2990"),
            stock_quantity=5,
        )
        cart = Cart.objects.create(user=customer)
        cart_item = CartItem.objects.create(cart=cart, variant=variant, quantity=1)

        output = run_purge("--apply", "--force-cart")

        self.assertFalse(Products.objects.filter(pk=self.demo_product.pk).exists())
        self.assertFalse(CartItem.objects.filter(pk=cart_item.pk).exists())
        self.assertIn("force", output.lower())

    def test_apply_skips_demo_product_with_a_customer_review(self):
        """ProductReviews.product_id cascades from Products too (catalog/models.py)
        -- a real customer's review is customer-authored content and gets the
        same skip-by-default treatment as a cart item."""
        reviewer = Users.objects.create_user(
            username="reviewer1", email="reviewer1@x.com", password="x",
            role="Customer", country="Bangladesh")
        review = ProductReviews.objects.create(
            review_images=[], rating=4.5, reviews="Great fit!",
            product_id=self.demo_product, review_user_id=reviewer,
        )

        output = run_purge("--apply")

        self.assertTrue(Products.objects.filter(pk=self.demo_product.pk).exists())
        self.assertTrue(ProductReviews.objects.filter(pk=review.pk).exists())
        self.assertIn("review", output.lower())

    def test_apply_skips_demo_product_with_a_customer_question(self):
        """ProductQuestions.product_id cascades from Products too -- same
        treatment as a cart item / review."""
        asker = Users.objects.create_user(
            username="asker1", email="asker1@x.com", password="x",
            role="Customer", country="Bangladesh")
        question = ProductQuestions.objects.create(
            question="Does this run true to size?", answer="",
            product_id=self.demo_product, question_user_id=asker,
        )

        output = run_purge("--apply")

        self.assertTrue(Products.objects.filter(pk=self.demo_product.pk).exists())
        self.assertTrue(ProductQuestions.objects.filter(pk=question.pk).exists())
        self.assertIn("question", output.lower())

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
