"""Select public editorial data for the news design; never reads private settings."""
import json
import urllib.request
from pathlib import Path

url = "https://nobleseek.fabrything.com/api/store/nobleseek/articles/?pageSize=24"
with urllib.request.urlopen(url, timeout=30) as response:
    data = json.load(response)
    rows = data.get("results", data.get("data", {}).get("results", []))
selected = [{key: row.get(key) for key in ("slug", "headline", "headline_bn", "excerpt", "hero_image", "category_name", "published_at")} for row in rows]
path = Path(__file__).resolve().parents[1] / ".superdesign/news-content.json"
path.write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Selected {len(selected)} public stories for the design.")
