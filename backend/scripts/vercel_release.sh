#!/bin/sh
set -eu
if [ "${VERCEL_ENV:-}" != "production" ]; then
  exit 0
fi
python manage.py migrate --noinput
if [ -n "${NEWS_SITE_URL:-}" ]; then
  python manage.py configure_news_domain --origin "$NEWS_SITE_URL" --if-default
fi
# Build-only opt-in; ordinary deployments preserve later editorial changes.
if [ "${NEWS_EDITORIAL_REFRESH:-}" = "2026-11-07" ]; then
  python manage.py reconcile_news_categories
  python manage.py cleanup_demo_news
  python manage.py reconcile_news_categories --apply
  python manage.py cleanup_demo_news --apply
fi
python manage.py publishing_capacity
