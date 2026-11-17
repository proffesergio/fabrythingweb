"""Verify public news markup and image fetches with Facebook's documented user-agent."""
import html
import json
import re
import urllib.request
from pathlib import Path

UA = "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"


def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30)


def main():
    audit = json.loads((Path(__file__).resolve().parents[1] / ".local-validation/seo-audit.json").read_text(encoding="utf-8"))
    articles = [row["url"] for row in audit if "/nobleseek/echolink-" in row["url"]]
    results = []
    for url in articles:
        with fetch(url) as response:
            source = response.read().decode("utf-8")
            assert response.status == 200
        tags = {key: html.unescape(value) for key, value in re.findall(r'<meta property="(og:[^"]+)" content="([^"]*)"', source)}
        assert tags.get("og:title") and tags.get("og:description")
        assert tags.get("og:type") == "article"
        assert tags.get("og:url") == url
        image = tags.get("og:image", "")
        assert image.startswith("https://")
        result = {"url": url, "facebook_user_agent_status": 200, "og_tags": tags}
        try:
            with fetch(image) as response:
                result.update(image_status=response.status, image_type=response.headers.get("Content-Type"))
                response.read(64)
                assert response.status == 200 and response.headers.get("Content-Type", "").startswith("image/")
        except Exception as error:
            result["image_error"] = str(error)
        results.append(result)
    report = Path(__file__).resolve().parents[1] / ".local-validation/facebook-preview-check.json"
    report.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    for result in results:
        print(json.dumps({key: value for key, value in result.items() if key != "og_tags"}, ensure_ascii=True))


if __name__ == "__main__":
    main()
