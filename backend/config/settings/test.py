"""Test settings — local SQLite, fully isolated from Neon/production.

Never connects to the Neon database configured via DATABASE_* env vars.
Django's test runner uses an in-memory SQLite database, so tests are fast and
leave no artifacts. Use for every test run:

    DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test <app>
"""

from .base import *  # noqa: F401,F403

DEBUG = False
ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test_db.sqlite3",  # noqa: F405 — test runner uses :memory: anyway
    }
}

# Never crash tests on a missing SECRET_KEY.
if not SECRET_KEY:  # noqa: F405
    SECRET_KEY = "test-insecure-key"

# base.py captured SIMPLE_JWT["SIGNING_KEY"] = SECRET_KEY at import time, when
# SECRET_KEY was still None (no .env in CI/fresh checkouts). Re-point it at the
# resolved key so JWT-authenticated API tests can sign tokens.
SIMPLE_JWT["SIGNING_KEY"] = SECRET_KEY  # noqa: F405

# Faster hashing keeps the suite quick.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
