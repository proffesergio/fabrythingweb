"""Read-only HTTP checks for crawl directives, publisher file and public documents."""
import concurrent.futures
import json
import re
import time
import urllib.error
import urllib.request
from xml.etree import ElementTree


def check(url):
    started = time.monotonic()
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Fabrything-SEO-Audit/1.0"})
        try:
            response = urllib.request.urlopen(request, timeout=35)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            body = response.read().decode("utf-8", errors="replace")
            result = {"url": url, "final_url": response.url, "status": response.status,
                      "seconds": round(time.monotonic() - started, 2),
                      "content_type": response.headers.get("Content-Type"),
                      "robots_header": response.headers.get("X-Robots-Tag"),
                      "cache": response.headers.get("X-Vercel-Cache"),
                      "canonical": re.findall(r'<link[^>]*rel=[\"\']canonical[\"\'][^>]*href=[\"\']([^\"\']+)', body),
                      "title": re.findall(r"<title>(.*?)</title>", body),
                      "h1": re.findall(r"<h1[^>]*>(.*?)</h1>", body),
                      "robots_meta": re.findall(r'<meta[^>]*name=[\"\']robots[\"\'][^>]*content=[\"\']([^\"\']+)', body),
                      "adsense": re.findall(r'<meta[^>]*name=[\"\']google-adsense-account[\"\'][^>]*content=[\"\']([^\"\']+)', body),
                      "adsense_scripts": body.count('adsbygoogle.js?client=ca-pub-1712742966437949'),
                      "og_image": re.findall(r'<meta[^>]*property=[\"\']og:image[\"\'][^>]*content=[\"\']([^\"\']+)', body),
                      "og_title": re.findall(r'<meta[^>]*property=[\"\']og:title[\"\'][^>]*content=[\"\']([^\"\']+)', body),
                      "bytes": len(body.encode("utf-8"))}
            if url.endswith(".txt") or response.status >= 400:
                result["body"] = body[:800]
            if url.endswith("sitemap.xml") and response.status == 200:
                result["locations"] = [node.text for node in ElementTree.fromstring(body).iter() if node.tag.endswith("}loc")]
            return result
    except Exception as error:
        return {"url": url, "error": str(error), "seconds": round(time.monotonic() - started, 2)}


def main():
    hosts = ["https://www.fabrything.com", "https://nobleseek.fabrything.com"]
    urls = [host + path for host in hosts for path in ("/ads.txt", "/robots.txt", "/sitemap.xml")]
    urls += ["https://fabrything.com/ads.txt", "https://www.fabrything.com/", "https://www.fabrything.com/blog",
             "https://nobleseek.fabrything.com/nobleseek", "https://nobleseek.fabrything.com/nobleseek/seo-audit-missing-page-404",
             "https://fabrythingapi.vercel.app/api/health/"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(check, urls))
        samples = []
        for result in results:
            for segment in ("/product/", "/nobleseek/", "/blog/"):
                locations = [url for url in result.get("locations", []) if segment in url]
                if locations:
                    samples.extend(locations[:2] + locations[-2:])
        results += list(executor.map(check, dict.fromkeys(samples)))
    from pathlib import Path
    report = Path(__file__).resolve().parents[1] / ".local-validation/seo-audit.json"
    report.parent.mkdir(exist_ok=True)
    report.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    for result in results:
        summary = {key: value for key, value in result.items() if key != "locations"}
        if "locations" in result:
            summary["sitemap_urls"] = len(result["locations"])
        print(json.dumps(summary, ensure_ascii=True))


if __name__ == "__main__":
    main()
