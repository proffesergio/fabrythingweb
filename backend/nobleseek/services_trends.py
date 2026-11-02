"""Trends fetcher — pytrends when available, curated fallback otherwise.

pytrends is unofficial scraping and breaks often, so:
- try pytrends trending_searches for BD (pn='bangladesh') + US
- on ANY failure, seed from a small evergreen BD-relevant pool so the
  cron never produces an empty inbox and admin always has work items.
"""
import logging
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)

FALLBACK_POOL = [
    ("বাংলাদেশ ক্রিকেট", "Sports", "BD"),
    ("ঈদ শপিং অফার", "Shopping", "BD"),
    ("SSC Result 2026", "Education", "BD"),
    ("বিশ্বকাপ ফুটবল", "Sports", "BD"),
    ("iPhone 17 price in Bangladesh", "Tech", "BD"),
    (" weather Dhaka", "News", "BD"),
    ("NobleSeek", "News", "BD"),
    ("Taylor Swift", "Entertainment", "US"),
    ("Bitcoin price", "Finance", "US"),
    ("iPhone 17", "Tech", "US"),
]


def _via_pytrends(geo: str, limit: int = 20):
    try:
        from pytrends.request import TrendReq
    except ImportError:
        return []
    try:
        tr = TrendReq(hl="en-US" if geo == "US" else "bn-BD",
                      tz=360, timeout=(10, 25), retries=1)
        pn = "united_states" if geo == "US" else "bangladesh"
        df = tr.trending_searches(pn=pn)
        out = []
        for i, kw in enumerate(df[0].tolist()[:limit]):
            out.append({"keyword": str(kw).strip(),
                        "score": max(10, 95 - i * 4),
                        "label": f"Trending #{i + 1} in {geo}",
                        "hint": ""})
        return out
    except Exception as exc:
        logger.warning("pytrends failed geo=%s: %s", geo, exc)
        return []


def fetch_and_store(limit_per_geo: int = 20) -> int:
    from .models import TrendKeyword
    cutoff = timezone.now() - timedelta(hours=20)
    created = 0
    for geo in ("BD", "US"):
        items = _via_pytrends(geo, limit_per_geo)
        if not items:  # fallback keeps inbox alive
            items = [{"keyword": k, "score": 60 - i * 2,
                      "label": "Curated fallback", "hint": h}
                     for i, (k, h, g) in enumerate(FALLBACK_POOL)
                     if g == geo][:8]
        for it in items:
            kw = (it["keyword"] or "").strip()
            if not kw:
                continue
            exists = TrendKeyword.objects.filter(
                keyword__iexact=kw, fetched_at__gte=cutoff).exists()
            if exists:
                continue
            TrendKeyword.objects.create(
                keyword=kw[:255], geo=geo,
                traffic_score=int(it.get("score", 50)),
                traffic_label=str(it.get("label", ""))[:60],
                category_hint=str(it.get("hint", ""))[:120])
            created += 1
    return created
