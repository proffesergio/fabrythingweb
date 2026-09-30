"""Traffic & user-activity storage for the plugin-based admin panel.

Two tables, deliberately small:

- AnalyticsProvider: one row per traffic plugin (ga4, gtm, meta_pixel,
  adsense, internal). Holds the *backend-known* config (measurement IDs,
  enabled flags) so the admin UI can show health per provider without
  scraping frontend env vars. The actual browser tags still live in
  frontend/.../public/index.html — this table is the control plane, not
  the tag itself.
- TrackedEvent: first-party event log fed by POST /api/store/analytics/ingest/
  (sendBeacon from utils/analytics.js). Powers the Traffic panel's funnel
  (page_view -> view_item -> add_to_cart -> begin_checkout -> purchase) when
  GA4/AdSense are blocked, pending approval, or just need a second source.

TrackedEvent intentionally has NO FK to the user model: guests generate most
traffic and would otherwise force nullable FKs + cross-app migration
dependencies. user_id is a plain integer snapshot.
"""

from django.db import models


class AnalyticsProvider(models.Model):
    PROVIDER_CHOICES = [
        ("ga4", "Google Analytics 4"),
        ("gtm", "Google Tag Manager"),
        ("meta_pixel", "Meta Pixel"),
        ("adsense", "Google AdSense"),
        ("internal", "Internal event log"),
    ]

    key = models.CharField(max_length=32, unique=True, choices=PROVIDER_CHOICES)
    name = models.CharField(max_length=64)
    is_enabled = models.BooleanField(default=True)
    # Free-form config the provider plugin reads, e.g.
    # {"measurement_id": "G-XXXX", "container_id": "GTM-XXXX", "pixel_id": "...",
    #  "publisher_id": "ca-pub-..."} — secrets never belong here.
    config = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        state = "on" if self.is_enabled else "off"
        return f"{self.name} ({state})"


class TrackedEvent(models.Model):
    event = models.CharField(max_length=64, db_index=True)
    path = models.CharField(max_length=512, blank=True, default="")
    session_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
    user_id = models.IntegerField(null=True, blank=True)
    params = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event", "created_at"]),
        ]

    def __str__(self):
        return f"{self.event} @ {self.created_at:%Y-%m-%d %H:%M}"
