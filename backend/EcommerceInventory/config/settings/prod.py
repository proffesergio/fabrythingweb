"""Production settings — strict and secure. Driven entirely by env vars."""

from .base import *  # noqa: F401,F403

DEBUG = False

# ALLOWED_HOSTS and CORS_ALLOWED_ORIGINS MUST be provided via env in prod.
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "")  # noqa: F405
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "")  # noqa: F405

# Security hardening
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
X_FRAME_OPTIONS = "DENY"

if not SECRET_KEY:  # noqa: F405
    raise RuntimeError("SECRET_KEY must be set in production.")

# Static files: WhiteNoise compresses and serves them from the app itself, so
# no separate CDN/nginx is needed on Render's free web service.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# Neon (managed Postgres) requires SSL. Default the prod connection to require it
# even if DATABASE_SSLMODE isn't explicitly set in the environment.
DATABASES["default"]["OPTIONS"]["sslmode"] = os.getenv("DATABASE_SSLMODE", "require")  # noqa: F405
