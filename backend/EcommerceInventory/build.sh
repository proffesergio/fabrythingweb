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

# seed_demo is idempotent (get_or_create) — safe to run on every deploy.
# Populates the store config + demo catalog so the storefront has data to show.
python manage.py seed_demo

# seed_food_modules is idempotent (update_or_create) — safe to run on every deploy.
# Registers the Food admin-panel menu modules.
python manage.py seed_food_modules

# seed_food_demo is idempotent (get_or_create by slug) — safe on every deploy.
# Seeds demo restaurants, delivery zones, and menus so the Food app has data.
python manage.py seed_food_demo
python manage.py seed_bd_store
