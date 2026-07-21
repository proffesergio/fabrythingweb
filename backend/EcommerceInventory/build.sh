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
python manage.py seed_demo --if-empty      || echo "WARNING: seed_demo failed (non-fatal)"
python manage.py seed_food_demo --if-empty || echo "WARNING: seed_food_demo failed (non-fatal)"

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
if [ "$PRUNE_ORPHAN_LOGINS" = "true" ]; then
  echo "PRUNE_ORPHAN_LOGINS=true — removing orphaned rider/restaurant logins:"
  python manage.py prune_orphan_logins            # report what is about to go
  python manage.py prune_orphan_logins --apply || echo "WARNING: prune failed (non-fatal)"
else
  # Always report, never delete — so a stranded account is visible in the build
  # log without needing shell access.
  python manage.py prune_orphan_logins || true
fi
