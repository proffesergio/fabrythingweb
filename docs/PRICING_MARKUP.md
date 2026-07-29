# Platform-revenue markup on product prices

Every product now carries a **platform markup** on top of its supplier/source
price, so the store earns revenue on every sale rather than just reselling at
cost. This document explains the rule, where to change it, how to run the
one-time backfill on the live 194-product catalog, and what changed in the
partner price sync.

## The rule

```
markup        = max(markup_floor, base_price * markup_percentage / 100)
selling_price = base_price + markup
```

This is the same shape as the restaurant commission rule in
`food/pricing.py` (`max(min_commission_amount, food_net * commission_percentage%)`):
a flat percentage alone loses almost all margin on a cheap item, and a flat
floor alone gives up nearly all upside on an expensive one. `max()` gets
both — a guaranteed minimum taka margin on cheap items that scales up on
expensive ones.

**Defaults: floor = ৳50, percentage = 3%.** The owner asked for "at least
50→100 BDT" of margin on cheap items; 3% comfortably clears that on anything
above ~৳1,700 and the floor protects everything below it.

### Worked examples (at the defaults)

| Base price (supplier cost) | 3% of base | Markup used (`max(50, 3%)`) | Selling price |
| --- | --- | --- | --- |
| ৳99 | ৳2.97 | **৳50** (floor wins) | **৳149** |
| ৳3,200 (catalog median) | ৳96.00 | **৳96** (percentage wins) | **৳3,296** |
| ৳989,900 (top of catalog) | ৳29,697.00 | **৳29,697** (percentage wins) | **৳1,019,597** |

The implementation lives in `catalog/pricing.py`:
`markup_for(base_price)` returns just the markup amount (mirrors
`food.pricing.commission_for`); `apply_markup(base_price)` returns the full
selling price and is the **only** function anything in the codebase should
ever call to turn a base price into a selling price.

## Where to change the floor and percentage

**Django admin → Core → Store Configuration** (the same single-row config
that already holds the fixed shipping rate, CoD toggle, WhatsApp numbers,
etc. — `core.models.StoreConfiguration`, `StoreConfiguration.get_solo()`).
Two new fields:

- `markup_percentage` — 0–100, clamped on save (a mis-typed `500` is clamped
  to `100`, not applied literally — that would have 6x'd every price on the
  site).
- `markup_floor` — clamped to ≥ 0.

Editing either takes effect immediately, no redeploy: every price-setting
path reads `StoreConfiguration.get_solo()` at the moment it runs. It does
**not** retroactively move existing product prices — those only change when
one of the paths below runs again (partner sync, or you re-run the backfill
command, though the backfill is a one-time thing — see below).

**Why `StoreConfiguration` and not a new singleton model, or
`DeliveryPricing`'s pattern?** Platform markup is a store-wide setting like
the fixed shipping rate — one number for the whole catalog — not a
per-order snapshot the way `DeliveryPricing` rates are (those get frozen
onto each food order at checkout so a rate change never moves past books).
Reusing `StoreConfiguration` means no new admin section to register or
explain; it already is the "global store settings" singleton.

## `base_price` — why re-running anything is safe

Every `Products` row now has a `base_price` field: the supplier/source price
**before** markup, nullable (the 194 pre-existing products have none yet
until the backfill runs).

**The selling price is always derived from `base_price`, never mutated in
place.** Every path that sets a price does:

```python
product.base_price = <the raw, pre-markup price>
product.initial_selling_price = apply_markup(product.base_price)
```

never `apply_markup(product.initial_selling_price)`. That is what makes
every one of these idempotent — re-running an import, a partner sync, or the
backfill recomputes the exact same selling price from the exact same
`base_price`, instead of stacking a second markup on top of the first. A
test (`catalog/test_apply_pricing_markup.py::test_running_apply_twice_changes_nothing`)
runs the backfill twice and asserts the price is bit-for-bit unchanged after
the second run.

`discount_price` follows the same rule: if a product has a discount, the
discount is treated as its own pre-markup base and marked up the same way
(`apply_markup(discount_base)`), so a sale price can never dip below cost —
a bare pass-through discount would otherwise let the site sell under the
supplier price.

### Every path that touches a price also updates the variant

Checkout charges `ProductVariant.effective_price` (`orders/services.py` →
`catalog/models.py`), **not** the `Products` row — the storefront showing
one price while checkout charges another is a bug this codebase has already
shipped once. Every path below mirrors its new `initial_selling_price` /
`discount_price` onto the product's **active** variants in the same
operation: product import (`catalog/services_import.py`), `seed_store_catalog`,
`sync_source_prices`, the admin quick-update endpoint, and the
`apply_pricing_markup` backfill.

## What happened to `RESELLER_MARKUP_PERCENT`

**Retired.** `catalog/services_price_sync.py` used to read this env var and
apply its own `factor = 1 + markup_percent/100` on top of the partner's
scraped price — a second, independent markup rule living outside
`catalog/pricing.py`. Once the unified `apply_markup()` rule existed, keeping
that env var alive would have marked up every partner (potakait.com /
canvasit.com.bd) product **twice**: once by the sync's own factor, once by
whatever else in the codebase applied the platform markup.

`sync_source_prices` now does this instead: the partner's live retail price
becomes the product's `base_price`, and the selling/discount prices are
re-derived through the same `apply_markup()` everything else uses.
`sync_source_prices()` no longer accepts a `markup_percent` argument at all —
there is exactly one markup rule in the codebase now, configured in one
place (Store Configuration), not an env var plus a database rule that could
drift apart or double up. If `RESELLER_MARKUP_PERCENT` is still set in the
Render dashboard it is simply unread now; it can be removed at any time with
no behavior change.

**Existing test numbers that legitimately changed** in
`catalog/test_price_sync.py` because of this unification (defaults
floor=50/3%, sample partner price ৳46,000 / discount ৳44,500):

| | Old expectation (double markup avoided) | New expectation |
| --- | --- | --- |
| `initial_selling_price` | 46,000.00 | **47,380.00** (46,000 + 3% = 1,380) |
| `discount_price` | 44,500.00 | **45,835.00** (44,500 + 3% = 1,335) |

`test_markup_applied` (which asserted on the old `markup_percent=` kwarg) was
replaced with `test_markup_comes_from_the_unified_pricing_config_not_an_env_var`,
which proves the markup now comes from `StoreConfiguration`, not an argument
or an env var. Two more pre-existing tests needed the same kind of numeric
update because `seed_product_entry` (shared by `seed_store_catalog` and the
admin import tool) now marks up prices at creation time too:
`catalog/test_seed_store_catalog.py::test_force_update_refreshes_existing_variant_price`
and `catalog/test_admin_product_import.py`'s import-creates-product test.

## Running the retroactive backfill (the 194 existing products)

**This is a management command, not a migration** — it changes what real
customers are charged, so the owner runs it deliberately rather than it
firing automatically on deploy.

```bash
python manage.py apply_pricing_markup            # dry run (default) -- prints
                                                  # a before/after price table
                                                  # and the total change, writes
                                                  # nothing
python manage.py apply_pricing_markup --apply    # actually write the new
                                                  # prices and update variants
```

It only ever touches products where `base_price` is still `NULL`. For each:
`base_price` is set to today's `initial_selling_price` (today's un-marked-up
price), then the new selling/discount prices are computed with
`apply_markup()` and mirrored onto active variants. A product that already
has a `base_price` (already migrated, or priced since by
`sync_source_prices` or a fresh import) is left completely alone — which is
also why a second `--apply` run is a safe no-op: nothing is left to migrate.

Any product whose price data can't be processed (e.g. a corrupted negative
price) is printed by name and reason under "Skipped" rather than silently
dropped from the run.

### Running it on Render (no shell on the free plan)

Mirrors the existing `PURGE_DEMO_CATALOG` two-stage pattern in `build.sh`:

1. Set the Render env var **`APPLY_PRICING_MARKUP=report`**, deploy, and read
   the dry-run before/after table in the build log.
2. Once it looks right, set **`APPLY_PRICING_MARKUP=apply`** and deploy again
   — this writes the new prices and updates variants.
3. **Remove the variable.** Leaving it set is harmless (the command is
   idempotent), but there's no reason to keep re-running it on every deploy.

**Do this soon, and before making further manual price edits** in the admin
quick-update tool on any of the pre-existing products: the backfill treats
`base_price = NULL` as "not migrated yet" and will use whatever
`initial_selling_price` currently holds as the pre-markup base. A manual edit
made in between would be treated as a new "supplier price" and get marked up
on top, rather than treated as the final customer-facing price it was meant
to be.

Take a Neon branch/backup before step 2, same advice as for
`PURGE_DEMO_CATALOG` — writing prices is easy to get right in a dry run and
still worth being able to roll back.
