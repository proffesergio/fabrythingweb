#!/usr/bin/env bash
# Render build step for the Fabrything Django API.
# Runs on every deploy: install deps, gather static files, apply migrations, seed.
set -o errexit

# manage.py defaults to config.settings.dev, so pin prod for every command here.
# (Render sets this via env too, but pinning makes the build self-contained.)
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.prod}"

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate

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
