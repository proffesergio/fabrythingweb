"""Gunicorn config, auto-loaded when gunicorn starts in this directory.

The default 30s worker timeout is too tight for a free-tier managed Postgres
(e.g. Neon) that suspends when idle: the first request after a cold start pays
the DB wake-up latency and can exceed 30s, killing the worker. A higher timeout
lets that first request through; the N+1 fixes in the storefront views keep
warm requests fast.
"""

import os

# Honor Render's WEB_CONCURRENCY if set, else a sane default for the free plan.
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
graceful_timeout = 30
# Recycle workers periodically to guard against slow memory growth.
max_requests = 500
max_requests_jitter = 50
