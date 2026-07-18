from django.core.management.base import BaseCommand
from accounts.models import Modules


MODULES = [
    # Parent: Food
    {
        'module_name': 'Food',
        'module_icon': 'Restaurant',
        'module_url': None,
        'display_order': 6,
        'parent': None,
    },
    {
        'module_name': 'Restaurants',
        'module_icon': 'Storefront',
        'module_url': '/manage/food/restaurants',
        'display_order': 1,
        'parent': 'Food',
    },
    {
        'module_name': 'Delivery Zones',
        'module_icon': 'Map',
        'module_url': '/manage/food/zones',
        'display_order': 2,
        'parent': 'Food',
    },
]

# The exact module_names we manage — anything else gets deactivated
MANAGED_NAMES = {m['module_name'] for m in MODULES}


class Command(BaseCommand):
    help = 'Register Food admin-panel modules (idempotent).'

    def handle(self, *args, **options):
        created = 0
        updated = 0

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
