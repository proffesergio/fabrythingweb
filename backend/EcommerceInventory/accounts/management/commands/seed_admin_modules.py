from django.core.management.base import BaseCommand
from accounts.models import Modules


MODULES = [
    # Parent: Dashboard
    {
        'module_name': 'Dashboard',
        'module_icon': 'Dashboard',
        'module_url': '/home',
        'display_order': 1,
        'parent': None,
    },
    # Parent: Products
    {
        'module_name': 'Products',
        'module_icon': 'Inventory',
        'module_url': None,
        'display_order': 2,
        'parent': None,
    },
    {
        'module_name': 'All Products',
        'module_icon': 'Inventory',
        'module_url': '/manage/product',
        'display_order': 1,
        'parent': 'Products',
    },
    {
        'module_name': 'Add Product',
        'module_icon': 'Add',
        'module_url': '/form/product',
        'display_order': 2,
        'parent': 'Products',
    },
    {
        'module_name': 'Categories',
        'module_icon': 'Category',
        'module_url': '/manage/category',
        'display_order': 3,
        'parent': 'Products',
    },
    # ── Product Import: a TOP-LEVEL group, deliberately ──────────────────
    #
    # These were first added as children of "Products" and the owner still
    # could not find them: a submenu is invisible until its parent is
    # expanded, while "Affiliate Products" (Rokomari) sat at the top level and
    # was the only import tool anyone could see. Same shape as that entry now,
    # so every source is discoverable without knowing where to dig.
    #
    # Each child opens /manage/import/<slug> — the generic picker with the
    # source pre-selected and locked.
    {
        'module_name': 'Product Import',
        'module_icon': 'CloudDownload',
        'module_url': None,
        'display_order': 11,
        'parent': None,
    },
    {
        'module_name': 'Import from Fabrilife',
        'module_icon': 'Checkroom',
        'module_url': '/manage/import/fabrilife',
        'display_order': 1,
        'parent': 'Product Import',
    },
    {
        'module_name': 'Import from Arogga',
        'module_icon': 'Inventory',
        'module_url': '/manage/import/arogga',
        'display_order': 2,
        'parent': 'Product Import',
    },
    {
        'module_name': 'Import from Canvasit',
        'module_icon': 'Store',
        'module_url': '/manage/import/canvasit',
        'display_order': 3,
        'parent': 'Product Import',
    },
    # Potakait is included for completeness, but its Cloudflare setup returns
    # 403 to Render's datacentre IPs — the same URL answers 200 from a normal
    # connection. Browsing it will fail until the partner allowlists us.
    {
        'module_name': 'Import from Potakait',
        'module_icon': 'Store',
        'module_url': '/manage/import/potakait',
        'display_order': 4,
        'parent': 'Product Import',
    },
    {
        'module_name': 'All Import Sources',
        'module_icon': 'Tune',
        'module_url': '/manage/product-import',
        'display_order': 5,
        'parent': 'Product Import',
    },
    # Parent: Orders
    {
        'module_name': 'Orders',
        'module_icon': 'Receipt',
        'module_url': None,
        'display_order': 3,
        'parent': None,
    },
    {
        'module_name': 'Store Orders',
        'module_icon': 'Store',
        'module_url': '/manage/salesorder',
        'display_order': 1,
        'parent': 'Orders',
    },
    {
        'module_name': 'Purchase Orders',
        'module_icon': 'Redeem',
        'module_url': '/manage/purchaseorder',
        'display_order': 2,
        'parent': 'Orders',
    },
    {
        'module_name': 'Create Purchase Order',
        'module_icon': 'Add',
        'module_url': '/create/po',
        'display_order': 3,
        'parent': 'Orders',
    },
    # Parent: Inventory
    {
        'module_name': 'Inventory',
        'module_icon': 'Warehouse',
        'module_url': None,
        'display_order': 4,
        'parent': None,
    },
    {
        'module_name': 'Warehouses',
        'module_icon': 'Warehouse',
        'module_url': '/manage/warehouse',
        'display_order': 1,
        'parent': 'Inventory',
    },
    # Parent: Settings
    {
        'module_name': 'Settings',
        'module_icon': 'Settings',
        'module_url': None,
        'display_order': 5,
        'parent': None,
    },
    {
        'module_name': 'Manage Users',
        'module_icon': 'AccountCircle',
        'module_url': '/manage/users',
        'display_order': 1,
        'parent': 'Settings',
    },
    {
        'module_name': 'Module URLs',
        'module_icon': 'Settings',
        'module_url': '/manage/moduleurls',
        'display_order': 2,
        'parent': 'Settings',
    },
    # Parent: Customers
    {
        'module_name': 'Customers',
        'module_icon': 'AccountCircle',
        'module_url': '/manage/customers',
        'display_order': 6,
        'parent': None,
    },
    # Live chat inbox -- a single page, so (like Customers above) it's a
    # top-level entry with its own module_url rather than a parent+children.
    {
        'module_name': 'Live Chat',
        'module_icon': 'Chat',
        'module_url': '/manage/chat/inbox',
        'display_order': 8,
        'parent': None,
    },
    # Homepage hero banners -- a single manager page, same reasoning as
    # Live Chat/Customers above.
    {
        'module_name': 'Banners',
        'module_icon': 'ViewCarousel',
        'module_url': '/manage/banners',
        'display_order': 9,
        'parent': None,
    },
    # Rokomari affiliate automation -- single manager page (search/bulk-add +
    # placement/schedule/link-type CRUD), same reasoning as Banners above.
    {
        'module_name': 'Affiliate Products',
        'module_icon': 'Storefront',
        'module_url': '/manage/affiliate',
        'display_order': 11,
        'parent': None,
    },
    # ── Food delivery vertical (unified here so this seeder never deletes it) ──
    {
        'module_name': 'Food',
        'module_icon': 'Restaurant',
        'module_url': None,
        'display_order': 7,
        'parent': None,
    },
    {
        'module_name': 'Food Dashboard',
        'module_icon': 'Dashboard',
        'module_url': '/manage/food/dashboard',
        'display_order': 1,
        'parent': 'Food',
    },
    {
        'module_name': 'Restaurants',
        'module_icon': 'Storefront',
        'module_url': '/manage/food/restaurants',
        'display_order': 2,
        'parent': 'Food',
    },
    {
        'module_name': 'Menu Management',
        'module_icon': 'Category',
        'module_url': '/manage/food/menu',
        'display_order': 3,
        'parent': 'Food',
    },
    {
        'module_name': 'Food Orders',
        'module_icon': 'ReceiptLong',
        'module_url': '/manage/food/orders',
        'display_order': 4,
        'parent': 'Food',
    },
    {
        'module_name': 'Delivery Zones',
        'module_icon': 'Map',
        'module_url': '/manage/food/zones',
        'display_order': 5,
        'parent': 'Food',
    },
    {
        'module_name': 'Coupons',
        'module_icon': 'Redeem',
        'module_url': '/manage/food/coupons',
        'display_order': 6,
        'parent': 'Food',
    },
    {
        'module_name': 'Riders',
        'module_icon': 'TwoWheeler',
        'module_url': '/manage/food/riders',
        'display_order': 7,
        'parent': 'Food',
    },
    {
        'module_name': 'Payments',
        'module_icon': 'Receipt',
        'module_url': '/manage/food/payments',
        'display_order': 8,
        'parent': 'Food',
    },
    {
        'module_name': 'Partner Applications',
        'module_icon': 'HowToReg',
        'module_url': '/manage/food/partners',
        'display_order': 9,
        'parent': 'Food',
    },
    {
        'module_name': 'Rider Cash',
        'module_icon': 'Payments',
        'module_url': '/manage/food/rider-cash',
        'display_order': 10,
        'parent': 'Food',
    },
    # ── Custom print-on-demand (SP6) ────────────────────────────────────
    {
        'module_name': 'Custom Printing',
        'module_icon': 'Checkroom',
        'module_url': None,
        'display_order': 10,
        'parent': None,
    },
    {
        'module_name': 'Print Requests',
        'module_icon': 'Checkroom',
        'module_url': '/manage/print/requests',
        'display_order': 1,
        'parent': 'Custom Printing',
    },
    {
        'module_name': 'Print Setup',
        'module_icon': 'Tune',
        'module_url': '/manage/print/setup',
        'display_order': 2,
        'parent': 'Custom Printing',
    },
]

# The exact module_names we manage — anything else gets deactivated
MANAGED_NAMES = {m['module_name'] for m in MODULES}


class Command(BaseCommand):
    help = 'Seed (and clean up) admin navigation modules'

    def handle(self, *args, **options):
        created = 0
        updated = 0

        # ── Delete any stale modules not in our managed list ─────────────
        stale_qs = Modules.objects.exclude(module_name__in=MANAGED_NAMES)
        stale_names = list(stale_qs.values_list('module_name', flat=True))
        if stale_names:
            stale_qs.delete()
            self.stdout.write(self.style.WARNING(
                f'  Deleted {len(stale_names)} stale module(s): {", ".join(stale_names)}'
            ))

        # ── First pass: upsert top-level (parent) modules ─────────────────
        parent_map = {}
        for m in MODULES:
            if m['parent'] is not None:
                continue
            obj, was_created = Modules.objects.update_or_create(
                module_name=m['module_name'],
                defaults={
                    'module_icon': m['module_icon'],
                    'module_url': m['module_url'],
                    'display_order': m['display_order'],
                    'is_menu': True,
                    'is_active': True,
                    'parent_id': None,
                }
            )
            parent_map[m['module_name']] = obj
            if was_created:
                created += 1
                self.stdout.write(f'  Created: {m["module_name"]}')
            else:
                updated += 1
                self.stdout.write(f'  Updated: {m["module_name"]}')

        # ── Second pass: upsert child modules ─────────────────────────────
        for m in MODULES:
            if m['parent'] is None:
                continue
            parent_obj = parent_map.get(m['parent'])
            if not parent_obj:
                try:
                    parent_obj = Modules.objects.get(module_name=m['parent'])
                    parent_map[m['parent']] = parent_obj
                except Modules.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'  Parent not found: {m["parent"]}'))
                    continue

            obj, was_created = Modules.objects.update_or_create(
                module_name=m['module_name'],
                defaults={
                    'module_icon': m['module_icon'],
                    'module_url': m['module_url'],
                    'display_order': m['display_order'],
                    'is_menu': True,
                    'is_active': True,
                    'parent_id': parent_obj,
                }
            )
            if was_created:
                created += 1
                self.stdout.write(f'  Created: {m["module_name"]} (under {m["parent"]})')
            else:
                updated += 1
                self.stdout.write(f'  Updated: {m["module_name"]} (under {m["parent"]})')

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. {created} created, {updated} updated.'
        ))
