"""
Root-level WSGI shim.

The canonical WSGI config lives in ``config/wsgi.py``. This module re-exports it
so that either ``gunicorn config.wsgi:application`` or ``gunicorn wsgi:application``
(and ``gunicorn wsgi.py``) resolves to the same Django application.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')

application = get_wsgi_application()
app = application  # alias for platforms that look for `app`
