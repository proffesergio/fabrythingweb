"""AI draft helper — OpenAI-compatible, graceful offline fallback.

If OPENAI_API_KEY (or AI_API_KEY + AI_BASE_URL) is set we request 3 Bangla
viral headline options + 800-word outline. Otherwise we return a safe
template scaffold so admin can still 1-click from a trend with no key.
Human MUST review before publish (AdSense thin-content rule).
"""
import json
import logging
import os

import requests

logger = logging.getLogger(__name__)

FALLBACK_BODY = """<p><strong>{keyword}</strong> এখন Google Trends-এ বাংলাদেশের সবচেয়ে আলোচিত বিষয়গুলোর একটি। পাঠকদের জন্য আমরা মূল তথ্যগুলো সহজ ভাষায় সাজিয়েছি।</p>
<h2>কেন {keyword} ট্রেন্ড করছে?</h2>
<p>এখানে ২-৩ প্যারায় প্রেক্ষাপট লিখুন: কবে, কোথায়, কারা জড়িত। সোর্স লিংক যোগ করুন।</p>
<h2>মূল আপডেট</h2>
<p>এখানে ৩-৪ প্যারায় বিস্তারিত লিখুন (কে কী বলল, পরিসংখ্যান, প্রতিক্রিয়া)। কমপক্ষে ৬০০-৮০০ শব্দ লক্ষ্য রাখুন যাতে in-article বিজ্ঞাপন ভালোভাবে বসে।</p>
<h2>পাঠকের জন্য যা জানা জরুরি</h2>
<ul><li>পয়েন্ট ১</li><li>পয়েন্ট ২</li><li>পয়েন্ট ৩</li></ul>
<h2>পরবর্তী আপডেট</h2>
<p>আমরা {keyword} নিয়ে নতুন তথ্য পেলেই এই প্রতিবেদন আপডেট করব। NobleSeek ফেসবুক পেজ ফলো করুন।</p>
<p><em>ছবি: নিজস্ব / সংগৃহীত (ক্রেডিট দিন)। তথ্যসূত্র যাচাই করে প্রকাশ করুন।</em></p>
"""


def ai_draft_for_keyword(keyword: str, geo: str = "BD",
                         category_hint: str = "") -> dict:
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AI_API_KEY", "")
    base = os.getenv("AI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("AI_MODEL", "gpt-4o-mini")
    headlines = [
        f"{keyword}: সর্বশেষ আপডেট ও বিস্তারিত | Latest Update",
        f"কেন ট্রেন্ডে {keyword}? যা জানা জরুরি",
        f"{keyword} নিয়ে বড় খবর — পুরো প্রতিবেদন",
    ]
    excerpt = (f"{keyword} কেন Google Trends-এ শীর্ষে, মূল তথ্য, প্রতিক্রিয়া "
               f"ও পরবর্তী আপডেট — NobleSeek-এর বিস্তারিত প্রতিবেদন পড়ুন।")
    body = FALLBACK_BODY.format(keyword=keyword)
    if not api_key:
        return {"headlines": headlines, "excerpt": excerpt, "body_html": body,
                "ai_generated": False}
    try:
        prompt = (
            f"Write 3 viral Bangla+English mix news headlines (max 90 chars each) "
            f"for trending keyword '{keyword}' (region {geo}, hint {category_hint}). "
            f"Then a 700-900 word Bangla news article in simple HTML (<p>,<h2>,<ul>) "
            f"with sections: why trending, main update, key facts, what's next. "
            f"No fabrication of quotes. Return JSON "
            f'{{"headlines":[...],"excerpt":"...","body_html":"..."}}.'
        )
        r = requests.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.7, "max_tokens": 2500,
                  "response_format": {"type": "json_object"}},
            timeout=45,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
        return {"headlines": data.get("headlines", headlines)[:3],
                "excerpt": data.get("excerpt", excerpt)[:300],
                "body_html": data.get("body_html", body),
                "ai_generated": True}
    except Exception as exc:  # never break admin flow on AI failure
        logger.warning("AI draft failed for %s: %s", keyword, exc)
        return {"headlines": headlines, "excerpt": excerpt,
                "body_html": body, "ai_generated": False,
                "warning": str(exc)[:200]}
