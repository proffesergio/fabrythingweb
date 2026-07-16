#!/usr/bin/env python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import Modules
from django.utils import timezone

# Get parent IDs
products_id = Modules.objects.filter(module_name="Products").values_list('id', flat=True).first()
inventory_id = Modules.objects.filter(module_name="Inventory").values_list('id', flat=True).first()
orders_id = Modules.objects.filter(module_name="Orders").values_list('id', flat=True).first()
users_id = Modules.objects.filter(module_name="Users").values_list('id', flat=True).first()

now = timezone.now()

# Add submenus
if products_id:
    Modules.objects.create(module_name="All Products", module_url="/products/list", parent_id_id=products_id, display_order=1, is_menu=True, is_active=True, created_at=now, updated_at=now)
    Modules.objects.create(module_name="Add Product", module_url="/products/add", parent_id_id=products_id, display_order=2, is_menu=True, is_active=True, created_at=now, updated_at=now)
    Modules.objects.create(module_name="Categories", module_url="/products/categories", parent_id_id=products_id, display_order=3, is_menu=True, is_active=True, created_at=now, updated_at=now)

if inventory_id:
    Modules.objects.create(module_name="All Inventory", module_url="/inventory/list", parent_id_id=inventory_id, display_order=1, is_menu=True, is_active=True, created_at=now, updated_at=now)
    Modules.objects.create(module_name="Warehouses", module_url="/inventory/warehouses", parent_id_id=inventory_id, display_order=2, is_menu=True, is_active=True, created_at=now, updated_at=now)

if orders_id:
    Modules.objects.create(module_name="All Orders", module_url="/orders/list", parent_id_id=orders_id, display_order=1, is_menu=True, is_active=True, created_at=now, updated_at=now)

if users_id:
    Modules.objects.create(module_name="All Users", module_url="/users/list", parent_id_id=users_id, display_order=1, is_menu=True, is_active=True, created_at=now, updated_at=now)

print(f"Total modules: {Modules.objects.count()}")
print("\nMenu structure:")
for m in Modules.objects.filter(parent_id__isnull=True):
    print(f"  - {m.module_name}")
    for s in Modules.objects.filter(parent_id=m.id):
        print(f"      - {s.module_name}")
