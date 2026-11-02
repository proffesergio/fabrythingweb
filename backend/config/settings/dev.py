"""Development settings — permissive, for local work only."""

from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Allow any origin locally so the CRA dev server (localhost:3000) just works.
CORS_ALLOW_ALL_ORIGINS = True

# Fall back to a throwaway key if the env doesn't set one, so dev never crashes.
if not SECRET_KEY:  # noqa: F405
    SECRET_KEY = "dev-insecure-key-change-me"
