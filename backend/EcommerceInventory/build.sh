#!/usr/bin/env bash
# Render build step for the Fabrything Django API.
# Runs on every deploy: install deps, gather static files, apply migrations, seed.
set -o errexit

# manage.py defaults to config.settings.dev, so pin prod for every command here.
# (Render sets this via env too, but pinning makes the build self-contained.)
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.prod}"

pip install -r requirements.txt
python manage.py collectstatic --no-input

# Migrations MUST apply. `set -o errexit` already aborts the deploy if this
# fails — that is deliberate: shipping a new frontend against an un-migrated
# database is what produced the "Server Error (500)" pages on the food admin
# panel (missing columns on food_foodorder / food_rider). Fail loudly here
# rather than serve a half-broken site.
python manage.py migrate
python manage.py showmigrations food

# Ensure a Super Admin exists. create_admin is idempotent (no-ops if the user is
# already there). Credentials come from Render env vars (never committed). This is
# essential on a FRESH database: without it you can't log in AND product seeding has
# no owner to attach to. Runs before seeding so seed_bd_store finds the owner.
if [ -n "$ADMIN_USERNAME" ] && [ -n "$ADMIN_EMAIL" ] && [ -n "$ADMIN_PASSWORD" ]; then
  python manage.py create_admin --username "$ADMIN_USERNAME" --email "$ADMIN_EMAIL" --password "$ADMIN_PASSWORD" || echo "admin already exists (skipped)"
else
  echo "WARNING: ADMIN_USERNAME/ADMIN_EMAIL/ADMIN_PASSWORD not set — skipping admin bootstrap."
fi

# Unified admin navigation (ecommerce + food + customers). Idempotent and the SINGLE
# source of truth for the Modules table — must succeed so the live sidebar always
# reflects the current module set. Do NOT also run seed_food_modules: the two seeders
# used to fight over this table and delete each other's menus.
python manage.py seed_admin_modules

# Demo/seed data — best-effort. A data-seed hiccup must never fail the whole deploy
# (which would keep the site on the old version). Migrations + nav above already applied.
# --if-empty: seed demo data only on a fresh/empty DB, so redeploys never clobber
# the real products/restaurants the owner enters.
#
# seed_demo (which calls seed_bd_store) is DISABLED here on purpose: the real
# catalog (Fabrilife fashion + the two partner computer stores, seeded via
# SEED_STORE_PRODUCTS below) is now live, and the owner wants only real
# products on the site. seed_bd_store's ~60 loremflickr-placeholder products
# are stale demo data at this point, not a fresh-DB bootstrap — leaving it
# enabled would keep reseeding a dummy catalog next to the real one on every
# empty-DB deploy. One-time cleanup of anything already seeded lives in
# `purge_demo_catalog` (dry-run by default, --apply to delete). seed_food_demo
# is a different app (food delivery, not this storefront) and stays on.
python manage.py seed_food_demo --if-empty || echo "WARNING: seed_food_demo failed (non-fatal)"

# Expanded store taxonomy (Fashion/Phones/Computers/Gadgets categories). Create-only
# and imageless, so it is cheap and safe on every deploy. Deliberately --categories-only:
# the full `seed_store_catalog` (no flag) downloads ~600 product images, compresses
# them and stores them via core.storage.save_file. That is minutes of build time and
# only ever needs to happen once, so it is opt-in below rather than run every deploy.
python manage.py seed_store_catalog --categories-only || echo "WARNING: seed_store_catalog failed (non-fatal)"

# One-off: seed the real products (Fabrilife fashion + the two partner computer
# stores) WITH their images. Images are content-addressed rows in the database
# (core.ImageBlob, served from /api/media/<sha256>/), so unlike local MEDIA_ROOT
# they survive Render's ephemeral filesystem. Opt-in and self-disarming, same
# pattern as RELEASE_LOGIN below: set SEED_STORE_PRODUCTS=true in the Render
# dashboard, deploy once, then REMOVE the variable — otherwise every later deploy
# pays the download cost again for nothing. The command is create-only, so a
# repeat run cannot overwrite prices or names an admin has edited.
if [ "$SEED_STORE_PRODUCTS" = "true" ]; then
  echo "SEED_STORE_PRODUCTS=true — seeding store products and images (slow, one-off):"
  python manage.py seed_store_catalog || echo "WARNING: product seeding failed (non-fatal)"
fi

# One-off: delete the ~60 loremflickr placeholder products seed_bd_store used to
# create, now that real products are live. DELETES ROWS, so it is opt-in and
# two-stage — there is no shell on Render's free plan, so this is the only way to
# run it against production:
#   1. set PURGE_DEMO_CATALOG=report  -> deploy, read the dry-run in the build log
#   2. set PURGE_DEMO_CATALOG=apply   -> deploy again to actually delete
#   3. REMOVE the variable.
# The dry run lists every product it would delete and, crucially, any live
# customer CART items / reviews / questions that would go with them. Products
# referenced by an order are always skipped. Take a Neon branch before step 2 —
# the delete is irreversible.
if [ -n "$PURGE_DEMO_CATALOG" ]; then
  echo "PURGE_DEMO_CATALOG=$PURGE_DEMO_CATALOG — demo catalog purge:"
  python manage.py purge_demo_catalog            # always print the dry run first
  if [ "$PURGE_DEMO_CATALOG" = "apply" ]; then
    python manage.py purge_demo_catalog --apply || echo "WARNING: purge failed (non-fatal)"
  fi
fi

# Delivery geography: the 13 Bancharampur unions + their villages. Runs on every
# deploy but is CREATE-ONLY — it adds anything missing and never overwrites a
# zone/village the admin has edited (see seed_bancharampur --force-update, and
# food/tests/test_seed_preserves_edits.py which pins that behaviour).
python manage.py seed_bancharampur || echo "WARNING: seed_bancharampur failed (non-fatal)"

# Settlement rows for orders delivered before the ledger existed. Idempotent.
python manage.py backfill_settlements || echo "WARNING: backfill_settlements failed (non-fatal)"

# One-off repair for login accounts stranded by a half-failed onboarding (the
# cause of the permanent "A user with that email/username already exists" on the
# Riders page). DELETES USERS, so it is opt-in: set PRUNE_ORPHAN_LOGINS=true in
# the Render dashboard, deploy once, then REMOVE the variable again. Only ever
# touches Rider/Restaurant accounts that no Rider or Restaurant row points at.
# Free a username/email held by an account that was never meant to own it — the
# would-be rider who signed up at /auth/signup and got a Customer account, so the
# admin can't onboard them from the Riders tab. DELETES A USER, so it is opt-in and
# self-disarming: set RELEASE_LOGIN=<username-or-email> in the Render dashboard,
# deploy once, then REMOVE the variable. Refuses admins, accounts owning a
# Rider/Restaurant, and anything with order history (see accounts/management/
# commands/release_login.py) — a wrong value fails the step, it does not guess.
if [ -n "$RELEASE_LOGIN" ]; then
  echo "RELEASE_LOGIN=$RELEASE_LOGIN — releasing this login:"
  python manage.py release_login "$RELEASE_LOGIN"            # report the cascade first
  python manage.py release_login "$RELEASE_LOGIN" --apply || echo "WARNING: release_login failed (non-fatal)"
fi

if [ "$PRUNE_ORPHAN_LOGINS" = "true" ]; then
  echo "PRUNE_ORPHAN_LOGINS=true — removing orphaned rider/restaurant logins:"
  python manage.py prune_orphan_logins            # report what is about to go
  python manage.py prune_orphan_logins --apply || echo "WARNING: prune failed (non-fatal)"
else
  # Always report, never delete — so a stranded account is visible in the build
  # log without needing shell access.
  python manage.py prune_orphan_logins || true
fi

# One-off: retroactively apply the platform-revenue markup (catalog/pricing.py
# apply_markup: max(markup_floor, base_price * markup_percentage%), admin-tunable
# on StoreConfiguration) to the ~194 products seeded/imported before this feature
# existed and so carry no base_price yet. CHANGES WHAT CUSTOMERS ARE CHARGED, so
# it is opt-in and two-stage exactly like PURGE_DEMO_CATALOG above — there is no
# shell on Render's free plan:
#   1. set APPLY_PRICING_MARKUP=report -> deploy, read the dry-run before/after
#      price table (and total change) in the build log.
#   2. set APPLY_PRICING_MARKUP=apply  -> deploy again to actually write the new
#      prices and mirror them onto active ProductVariant rows.
#   3. REMOVE the variable.
# Idempotent: a product that already has base_price set (already migrated, or
# priced by sync_source_prices/import since) is left completely alone, so an
# accidental extra deploy with the variable still set changes nothing. See
# docs/PRICING_MARKUP.md.
if [ -n "$APPLY_PRICING_MARKUP" ]; then
  echo "APPLY_PRICING_MARKUP=$APPLY_PRICING_MARKUP — pricing markup backfill:"
  python manage.py apply_pricing_markup            # always print the dry run first
  if [ "$APPLY_PRICING_MARKUP" = "apply" ]; then
    python manage.py apply_pricing_markup --apply || echo "WARNING: pricing markup backfill failed (non-fatal)"
  fi
fi

# One-off: backfill size_chart on the 64 already-seeded Fabrilife products
# (catalog.services_size_chart_backfill) by looking each one up by exact name
# on fabrilife.com's own public search and reading the chart straight off the
# search hit -- they have no source_url to refetch by URL (fabrilife.com is a
# one-time seed source, not a reseller partner). Makes outbound network
# requests but only ever writes size_chart, never price/images/etc, so it is
# opt-in and two-stage exactly like PURGE_DEMO_CATALOG/APPLY_PRICING_MARKUP
# above — there is no shell on Render's free plan:
#   1. set BACKFILL_FABRILIFE_SIZE_CHART=report -> deploy, read the dry-run
#      (which products matched, which had no chart, which didn't match) in
#      the build log.
#   2. set BACKFILL_FABRILIFE_SIZE_CHART=apply  -> deploy again to actually
#      write size_chart onto the matched products.
#   3. REMOVE the variable.
# Idempotent: a product that already has a size_chart is never a candidate
# again, so an accidental extra deploy with the variable still set changes
# nothing. See docs/PRODUCT_DETAILS.md.
if [ -n "$BACKFILL_FABRILIFE_SIZE_CHART" ]; then
  echo "BACKFILL_FABRILIFE_SIZE_CHART=$BACKFILL_FABRILIFE_SIZE_CHART — size chart backfill:"
  python manage.py backfill_fabrilife_size_chart            # always print the dry run first
  if [ "$BACKFILL_FABRILIFE_SIZE_CHART" = "apply" ]; then
    python manage.py backfill_fabrilife_size_chart --apply || echo "WARNING: size chart backfill failed (non-fatal)"
  fi
fi

# One-off: audit and clean up rogue Admin/Staff/Super Admin accounts left by
# the now-closed public /api/auth/signup/ hole (accounts/controllers/
# AuthController.py -- it handed out role="Admin" to anyone who posted to it).
# Production verification created a real one this way: username
# __probe_no_create, role Admin. Always list every back-office account
# (read-only, cheap) so strays are visible in the build log without needing
# Render shell access (the free plan has none); deletion is opt-in and
# two-stage exactly like PURGE_DEMO_CATALOG above, because it removes users:
#   1. set ROGUE_ADMIN_ACCOUNTS=<comma-separated usernames/emails>, deploy --
#      the dry-run cascade + SAFE/REFUSED verdict for each prints in the log.
#   2. also set PURGE_ROGUE_ADMINS=apply, deploy again to delete only the
#      ones marked SAFE. An account with ANY order/content history (or that
#      itself created other accounts) is refused automatically, never
#      deleted -- see accounts/management/commands/audit_admin_accounts.py.
#   3. REMOVE both variables.
python manage.py audit_admin_accounts || true
if [ -n "$ROGUE_ADMIN_ACCOUNTS" ]; then
  echo "ROGUE_ADMIN_ACCOUNTS=$ROGUE_ADMIN_ACCOUNTS — auditing named admin accounts:"
  python manage.py audit_admin_accounts "$ROGUE_ADMIN_ACCOUNTS"
  if [ "$PURGE_ROGUE_ADMINS" = "apply" ]; then
    python manage.py audit_admin_accounts "$ROGUE_ADMIN_ACCOUNTS" --apply || echo "WARNING: audit_admin_accounts --apply failed (non-fatal)"
  fi
fi
