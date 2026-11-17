"""Record the deliberately selected public UI context without changing other targets."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
paths = [
    ".superdesign/nobleseek-design-system.md", ".superdesign/news-content.json",
    "frontend/src/nobleseek/pages/NobleSeekListPage.js",
    "frontend/src/nobleseek/components/NewsCards.js",
    "frontend/src/nobleseek/components/MostRead.js",
    "frontend/src/nobleseek/components/PollWidget.js",
    "frontend/src/nobleseek/portal/PortalHeader.js",
    "frontend/src/nobleseek/portal/NewsFooter.js",
    "frontend/src/nobleseek/layout/NobleSeekLayout.js",
    "frontend/src/nobleseek/NewsFonts.js", "frontend/src/nobleseek/ads/AdSlot.js",
]
for name in paths:
    path = (root / name).resolve()
    assert path.is_relative_to(root) and path.is_file()
state_path = root / ".superdesign/resume.json"
state = json.loads(state_path.read_text(encoding="utf-8-sig"))
logo = "frontend-public-nobleseek-logo-wide.png"
draft = "361ec0de-05f0-4501-8301-aaa76fcc02da"
approved = "--approved" in sys.argv or "--complete" in sys.argv
complete = "--complete" in sys.argv
state["targets"]["/nobleseek"] = {
    "targetKind": "existing-target", "projectId": "2588e80e-e4e8-4fb0-8db5-afea00e61257",
    "activeDraftId": draft, "baselineDraftId": draft,
    "designSystemPath": paths[0], "contextFiles": paths,
    "fingerprints": {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in paths},
    "referenceIds": [logo, "f8c6f923-55d2-4732-bd53-7c73b85b05ac"],
    "brandAssets": {"logo": {"assetKey": logo, "sourcePath": "frontend/public/nobleseek-logo-wide.png",
        "url": "https://vgbujcuwptvheqijyjbe.supabase.co/storage/v1/object/public/hmac-uploads/projects/2588e80e-e4e8-4fb0-8db5-afea00e61257/brand-assets/frontend-public-nobleseek-logo-wide.png/nobleseek-logo-wide.png"}},
    "drafts": {draft: {"title": "NobleSeek Modern Editorial Homepage",
        "visualDirection": "Dense modern Bangla newspaper; original navy/orange identity; real published stories",
        "currentVersion": 3}},
    "implementation": {"approved": approved, "completed": complete, "status": "Approved desktop design implemented and verified." if complete else "Owner approved implementation; checks pending." if approved else "Awaiting owner review of the desktop draft; SEO release is already live."},
    "updatedAt": datetime.now(timezone.utc).isoformat(),
}
temporary = state_path.with_suffix(".tmp.json")
temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
temporary.replace(state_path)
print("Recorded /nobleseek design and preserved other targets.")
