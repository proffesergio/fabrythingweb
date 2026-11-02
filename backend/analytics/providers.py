"""Provider plugin registry.

Each provider is a small class describing one traffic source: how the admin
Traffic panel checks its health and what "set up" means for it. Adding a new
source (e.g. TikTok Pixel) is: subclass BaseProvider, append to REGISTRY,
add the key to AnalyticsProvider.PROVIDER_CHOICES. No view changes needed —
the admin overview view renders whatever is registered.
"""

from dataclasses import dataclass, field


@dataclass
class ProviderStatus:
    key: str
    name: str
    is_enabled: bool
    configured: bool
    detail: str
    setup_url: str = ""
    docs_hint: str = ""


class BaseProvider:
    key = ""
    name = ""
    setup_url = ""
    docs_hint = ""

    def status(self, row=None) -> ProviderStatus:
        raise NotImplementedError


class GA4Provider(BaseProvider):
    key = "ga4"
    name = "Google Analytics 4"
    setup_url = "https://analytics.google.com/"
    docs_hint = "Measurement ID lives in Vercel env REACT_APP_GA4_MEASUREMENT_ID (fallback G-S32TZJZCLV)."

    def status(self, row=None) -> ProviderStatus:
        mid = (row.config.get("measurement_id") if row else "") or "G-S32TZJZCLV"
        return ProviderStatus(
            key=self.key, name=self.name,
            is_enabled=bool(row.is_enabled) if row else True,
            configured=bool(mid and mid.startswith("G-")),
            detail=f"Measurement ID {mid}" if mid else "No measurement ID recorded",
            setup_url=self.setup_url, docs_hint=self.docs_hint,
        )


class GTMProvider(BaseProvider):
    key = "gtm"
    name = "Google Tag Manager"
    setup_url = "https://tagmanager.google.com/"
    docs_hint = "Create the fabrything.com container, set REACT_APP_GTM_ID=GTM-XXXXXXX in Vercel, redeploy."

    def status(self, row=None) -> ProviderStatus:
        cid = (row.config.get("container_id") if row else "") or ""
        return ProviderStatus(
            key=self.key, name=self.name,
            is_enabled=bool(row.is_enabled) if row else True,
            configured=bool(cid.startswith("GTM-")),
            detail=f"Container {cid}" if cid else "No container linked — snippet no-ops until REACT_APP_GTM_ID is set",
            setup_url=self.setup_url, docs_hint=self.docs_hint,
        )


class MetaPixelProvider(BaseProvider):
    key = "meta_pixel"
    name = "Meta Pixel"
    setup_url = "https://business.facebook.com/events_manager2/"
    docs_hint = "Pixel ID is hardcoded in public/index.html (442368228898246)."

    def status(self, row=None) -> ProviderStatus:
        pid = (row.config.get("pixel_id") if row else "") or "442368228898246"
        return ProviderStatus(
            key=self.key, name=self.name,
            is_enabled=bool(row.is_enabled) if row else True,
            configured=bool(pid),
            detail=f"Pixel {pid}, PageView + mapped e-commerce events",
            setup_url=self.setup_url, docs_hint=self.docs_hint,
        )


class AdSenseProvider(BaseProvider):
    key = "adsense"
    name = "Google AdSense"
    setup_url = "https://www.google.com/adsense/"
    docs_hint = "Approval needs: ads.txt served, privacy page (/privacy ✓), real traffic. Set REACT_APP_ADSENSE_CLIENT after approval."

    def status(self, row=None) -> ProviderStatus:
        pub = (row.config.get("publisher_id") if row else "") or ""
        ok = pub.startswith("ca-pub-") and "XXXX" not in pub
        return ProviderStatus(
            key=self.key, name=self.name,
            is_enabled=bool(row.is_enabled) if row else True,
            configured=ok,
            detail=f"Publisher {pub}" if ok else "ads.txt serves a placeholder — replace with your pub ID after approval",
            setup_url=self.setup_url, docs_hint=self.docs_hint,
        )


class InternalLogProvider(BaseProvider):
    key = "internal"
    name = "Internal event log"
    setup_url = ""
    docs_hint = "First-party beacon log — works even when GA4 is blocked or pending."

    def status(self, row=None) -> ProviderStatus:
        from .models import TrackedEvent
        count = TrackedEvent.objects.count()
        return ProviderStatus(
            key=self.key, name=self.name,
            is_enabled=bool(row.is_enabled) if row else True,
            configured=True,
            detail=f"{count} events stored",
            setup_url=self.setup_url, docs_hint=self.docs_hint,
        )


REGISTRY: list = [GA4Provider(), GTMProvider(), MetaPixelProvider(), AdSenseProvider(), InternalLogProvider()]

#: Default rows seeded on first overview hit (and by seed_admin_modules'
#: companion — see analytics/management note in views.py).
DEFAULT_PROVIDERS: list = [
    {"key": "ga4", "name": "Google Analytics 4", "is_enabled": True,
     "config": {"measurement_id": "G-S32TZJZCLV"}},
    {"key": "gtm", "name": "Google Tag Manager", "is_enabled": True, "config": {}},
    {"key": "meta_pixel", "name": "Meta Pixel", "is_enabled": True,
     "config": {"pixel_id": "442368228898246"}},
    {"key": "adsense", "name": "Google AdSense", "is_enabled": True, "config": {}},
    {"key": "internal", "name": "Internal event log", "is_enabled": True, "config": {}},
]


def ensure_default_providers():
    """Idempotent — safe to call on every overview request and every deploy."""
    from .models import AnalyticsProvider
    for defaults in DEFAULT_PROVIDERS:
        AnalyticsProvider.objects.get_or_create(
            key=defaults["key"],
            defaults={"name": defaults["name"], "is_enabled": defaults["is_enabled"],
                      "config": defaults["config"]},
        )
