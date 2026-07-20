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

# Unified admin navigation (ecommerce + food + customers). Idempotent and the SINGLE
# source of truth for the Modules table — must succeed so the live sidebar always
# reflects the current module set. Do NOT also run seed_food_modules: the two seeders
# used to fight over this table and delete each other's menus.
python manage.py seed_admin_modules

# Demo/seed data — best-effort. A data-seed hiccup must never fail the whole deploy
# (which would keep the site on the old version). Migrations + nav above already applied.
python manage.py seed_demo      || echo "WARNING: seed_demo failed (non-fatal)"
python manage.py seed_food_demo || echo "WARNING: seed_food_demo failed (non-fatal)"
