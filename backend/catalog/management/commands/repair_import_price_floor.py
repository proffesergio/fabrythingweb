"""Raise under-floor supplier-linked prices from their recorded base cost.

Dry run by default. Discounted products are reported but skipped because the
raw discounted supplier amount is not stored; a normal price sync can quote
those products accurately. Never derives a price from the current shelf price.
"""
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import Products
from catalog.pricing import apply_markup
from core.models import StoreConfiguration


class Command(BaseCommand):
    help = 'Report or repair supplier-linked products below the configured profit floor.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Write the reviewed increases.')

    def handle(self, *args, **options):
        floor = Decimal(str(StoreConfiguration.get_solo().markup_floor))
        changes = []
        skipped = []
        products = Products.objects.exclude(source_url='').filter(base_price__isnull=False).order_by('id')
        for product in products:
            try:
                base = Decimal(str(product.base_price))
                current = Decimal(str(product.initial_selling_price))
                if not base.is_finite() or base <= 0 or not current.is_finite():
                    raise ValueError('invalid base or selling price')
            except (InvalidOperation, TypeError, ValueError):
                skipped.append((product, 'invalid base or selling price'))
                continue
            if current >= base + floor:
                continue
            if product.discount_price is not None:
                skipped.append((product, 'discounted product needs a source price sync'))
                continue
            target = max(current, apply_markup(base))
            changes.append((product, current, target))

        for product, old, new in changes:
            self.stdout.write(f'#{product.id} {product.sku}: {old:.2f} -> {new:.2f} BDT')
        for product, reason in skipped:
            self.stdout.write(f'#{product.id} {product.sku}: skipped ({reason})')
        self.stdout.write(f'{len(changes)} price(s) to raise; {len(skipped)} skipped.')
        if not options['apply']:
            self.stdout.write('Dry run; add --apply to write these changes.')
            return
        with transaction.atomic():
            for product, old, new in changes:
                # Recheck under a row lock so a concurrent admin edit or price
                # sync is never overwritten by a stale dry-run calculation.
                locked = Products.objects.select_for_update().get(pk=product.pk)
                if (locked.discount_price is not None or locked.base_price != product.base_price or
                        Decimal(str(locked.initial_selling_price)) != old):
                    continue
                locked.initial_selling_price = new
                locked.save(update_fields=['initial_selling_price', 'updated_at'])
                # Preserve hand-set variant overrides. Only variants still
                # carrying the same old shelf price inherit the repair.
                locked.variants.filter(is_active=True, price=old,
                                       discount_price__isnull=True).update(price=new)
        self.stdout.write('Applied eligible price increases.')
