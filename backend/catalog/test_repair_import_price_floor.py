from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from accounts.models import Users
from catalog.models import Categories, Products, ProductVariant


class RepairImportPriceFloorTests(TestCase):
    def setUp(self):
        owner = Users.objects.create_user(username='owner', email='owner@example.com',
                                          password='x', role='Super Admin', country='Bangladesh')
        category = Categories.objects.create(name='Test', slug='test', description='')
        self.product = Products.objects.create(
            name='Supplier item', slug='supplier-item', sku='FS-9010',
            category_id=category, description='', initial_buying_price=1000,
            initial_selling_price=1299, base_price=1290,
            source_url='https://potakait.com/item', domain_user_id=owner,
            added_by_user_id=owner)
        self.variant = ProductVariant.objects.create(product=self.product, sku='FS-9010-1', price=1299)

    def test_dry_run_and_apply_raise_existing_import_without_stacking(self):
        output = StringIO()
        call_command('repair_import_price_floor', stdout=output)
        self.product.refresh_from_db()
        self.assertEqual(self.product.initial_selling_price, 1299)
        self.assertIn('1299.00 -> 1340.00', output.getvalue())

        call_command('repair_import_price_floor', '--apply', stdout=StringIO())
        self.product.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual(self.product.initial_selling_price, 1340)
        self.assertEqual(self.variant.price, 1340)
        self.assertEqual(self.product.base_price, 1290)
        call_command('repair_import_price_floor', '--apply', stdout=StringIO())
        self.product.refresh_from_db()
        self.assertEqual(self.product.initial_selling_price, 1340)

    def test_discounted_product_is_skipped_without_raw_discount_cost(self):
        self.product.discount_price = 1299
        self.product.save(update_fields=['discount_price'])
        output = StringIO()
        call_command('repair_import_price_floor', '--apply', stdout=output)
        self.product.refresh_from_db()
        self.assertEqual(self.product.initial_selling_price, 1299)
        self.assertIn('needs a source price sync', output.getvalue())

    def test_hand_set_variant_price_is_preserved(self):
        custom = ProductVariant.objects.create(product=self.product, sku='FS-9010-2',
                                               size='L', price=1600)
        call_command('repair_import_price_floor', '--apply', stdout=StringIO())
        custom.refresh_from_db()
        self.assertEqual(custom.price, 1600)
