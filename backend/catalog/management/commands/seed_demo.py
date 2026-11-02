"""
One-shot demo seeder for the COD storefront.

Runs the curated clothing catalog seeder, then derives a sellable
ProductVariant (with stock) for every product size, and ensures the global
StoreConfiguration exists. Idempotent: safe to run repeatedly.

    python manage.py seed_demo
"""
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import Products, ProductVariant
from core.models import StoreConfiguration


def stock_for(product_id, index):
    """Deterministic, varied stock so the demo shows in-stock, low-stock, and sold-out."""
    if (product_id + index) % 13 == 0:
        return 0  # occasional sold-out variant
    return ((product_id * 7 + index * 5) % 25) + 4  # 4..28


class Command(BaseCommand):
    help = "Seed the full demo store: catalog + variants/stock + store configuration."

    def add_arguments(self, parser):
        parser.add_argument("--skip-catalog", action="store_true",
                            help="Skip the clothing catalog seeder (only build variants + config).")
        parser.add_argument("--if-empty", action="store_true",
                            help="Only seed the demo catalog when no products exist yet "
                                 "(protects real data on redeploys).")

    @transaction.atomic
    def handle(self, *args, **options):
        # 1) Store configuration (fixed COD shipping applied to every order).
        cfg, _ = StoreConfiguration.objects.get_or_create(pk=1)
        cfg.fixed_shipping_rate = Decimal("60.00")
        cfg.free_shipping_threshold = None  # true flat rate on all orders
        cfg.cod_enabled = True
        cfg.currency = "BDT"
        cfg.store_name = "Fabrything"
        cfg.save()
        self.stdout.write(self.style.SUCCESS("Store configuration ready (flat BDT 60 COD shipping)."))

        # 2) Catalog (real-brand, multi-category Bangladeshi storefront).
        #    seed_bd_store CLEARS + reseeds, so guard it behind --if-empty on deploys
        #    to never clobber real products the owner has entered.
        if options["if_empty"] and Products.objects.exists():
            self.stdout.write("Products already exist — skipping demo catalog (--if-empty).")
        elif not options["skip_catalog"]:
            self.stdout.write("Seeding branded multi-category catalog...")
            call_command("seed_bd_store")

        # 3) Variants + stock for every product.
        created, skipped = 0, 0
        for product in Products.objects.all().iterator():
            if product.variants.exists():
                skipped += 1
                continue

            base_price = Decimal(str(product.initial_selling_price or 0))
            disc = product.discount_price
            disc_price = Decimal(str(disc)) if disc else None

            sizes = product.available_sizes if isinstance(product.available_sizes, list) else []
            sizes = [s for s in sizes if s] or [""]  # at least a "one size" variant

            base_sku = (product.sku or f"P{product.id}").replace(" ", "").upper()
            for i, size in enumerate(sizes):
                sku = f"{base_sku}-{size or 'OS'}"
                # ensure unique sku
                if ProductVariant.objects.filter(sku=sku).exists():
                    sku = f"{sku}-{product.id}"
                ProductVariant.objects.create(
                    product=product,
                    sku=sku,
                    size=size,
                    color=product.color or "",
                    price=base_price,
                    discount_price=disc_price,
                    stock_quantity=stock_for(product.id, i),
                    weight_grams=int(product.weight * 1000) if product.weight else 300,
                    is_active=True,
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Variants: {created} created, {skipped} products already had variants."
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Done. Products: {Products.objects.count()}, Variants: {ProductVariant.objects.count()}."
        ))
