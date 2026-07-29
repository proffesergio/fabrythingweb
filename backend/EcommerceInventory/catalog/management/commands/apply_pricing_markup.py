"""Retroactively apply the platform markup (catalog/pricing.py apply_markup)
to the existing catalog -- the ~194 products seeded/imported before this
feature existed, which carry no `base_price` and no markup at all.

For every product with `base_price` still NULL:
    base_price          = today's initial_selling_price (today's un-marked-up price)
    new initial_selling_price = apply_markup(base_price)
    new discount_price        = apply_markup(old discount_price) if it had one

Once a product has a `base_price`, this command never touches it again -- so
a product already migrated (by this command, by `sync_source_prices`, or by
an import/seed that set base_price at creation) is left exactly alone. That
is what makes a second `--apply` a no-op: nothing left with base_price NULL,
nothing to do.

Deliberately NOT a migration -- this changes what real customers are
charged, so it must be run on purpose and reviewed first. Dry run by default,
same convention as `purge_demo_catalog`/`prune_orphan_logins`:

    python manage.py apply_pricing_markup            # report only
    python manage.py apply_pricing_markup --apply     # actually write

Skips nothing silently: any product whose current price data can't be
processed (missing/negative/non-numeric initial_selling_price) is reported
by name and reason rather than silently dropped from the run.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import Products
from catalog.pricing import apply_markup


class Command(BaseCommand):
    help = ("Backfill base_price and the platform markup onto products that predate "
           "this feature. Dry run by default.")

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true",
                            help="Actually write the new prices. Without this it only reports.")

    def handle(self, *args, **options):
        apply = options["apply"]

        candidates = Products.objects.filter(base_price__isnull=True).order_by("id")
        already_migrated = Products.objects.filter(base_price__isnull=False).count()

        rows, skipped = [], []
        for product in candidates:
            try:
                base = float(product.initial_selling_price)
            except (TypeError, ValueError):
                skipped.append((product, f"initial_selling_price is not a number: "
                                        f"{product.initial_selling_price!r}"))
                continue
            if base < 0:
                skipped.append((product, f"initial_selling_price is negative: {base}"))
                continue

            old_discount = product.discount_price
            try:
                old_discount = float(old_discount) if old_discount is not None else None
            except (TypeError, ValueError):
                skipped.append((product, f"discount_price is not a number: {product.discount_price!r}"))
                continue
            if old_discount is not None and old_discount < 0:
                skipped.append((product, f"discount_price is negative: {old_discount}"))
                continue

            new_selling = apply_markup(base)
            new_discount = apply_markup(old_discount) if old_discount is not None else None
            rows.append({
                "product": product,
                "base_price": base,
                "old_selling": product.initial_selling_price,
                "new_selling": new_selling,
                "old_discount": old_discount,
                "new_discount": new_discount,
            })

        self.stdout.write(
            f"{already_migrated} product(s) already have a base_price -- left alone.")
        self.stdout.write(
            f"{len(rows) + len(skipped)} product(s) have no base_price yet "
            f"({len(rows)} processable, {len(skipped)} skipped -- see below).\n")

        if rows:
            self.stdout.write(
                f"{'id':>6}  {'sku':<12} {'name':<32} {'old price':>12} {'new price':>12} "
                f"{'old disc':>12} {'new disc':>12}")
            total_change = 0.0
            for r in rows:
                p = r["product"]
                total_change += r["new_selling"] - r["old_selling"]
                old_disc_s = f"{r['old_discount']:.2f}" if r["old_discount"] is not None else "-"
                new_disc_s = f"{r['new_discount']:.2f}" if r["new_discount"] is not None else "-"
                self.stdout.write(
                    f"{p.id:>6}  {p.sku:<12} {(p.name or '')[:32]:<32} "
                    f"{r['old_selling']:>12.2f} {r['new_selling']:>12.2f} "
                    f"{old_disc_s:>12} {new_disc_s:>12}")
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nTotal selling-price change across {len(rows)} product(s): "
                    f"{total_change:+.2f} BDT."))
        else:
            self.stdout.write("Nothing to do -- no product needs a price change.")

        if skipped:
            self.stdout.write(self.style.WARNING(
                f"\nSkipped {len(skipped)} product(s) that could not be processed "
                f"(reported, not silently dropped):"))
            for product, reason in skipped:
                self.stdout.write(f"  #{product.id:<5} {product.sku:<12} {product.name!r:<40} -- {reason}")

        if not apply:
            self.stdout.write(self.style.WARNING(
                "\nDry run -- nothing written. Re-run with --apply to write these prices."))
            return

        if not rows:
            self.stdout.write(self.style.SUCCESS("\nNothing to apply."))
            return

        with transaction.atomic():
            for r in rows:
                product = r["product"]
                product.base_price = r["base_price"]
                product.initial_selling_price = r["new_selling"]
                product.discount_price = r["new_discount"]
                product.save(update_fields=[
                    "base_price", "initial_selling_price", "discount_price", "updated_at"])
                # Checkout charges ProductVariant.effective_price, not this row
                # (orders/services.py) -- same precedent as
                # services_price_sync.sync_source_prices and the admin
                # quick-update endpoint. Only active variants: an
                # inactive/retired SKU is not sellable and re-pricing it is
                # not observable anyway.
                product.variants.filter(is_active=True).update(
                    price=r["new_selling"], discount_price=r["new_discount"])

        self.stdout.write(self.style.SUCCESS(
            f"\nApplied the platform markup to {len(rows)} product(s)."))
