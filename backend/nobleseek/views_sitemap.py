"""XML sitemap for the news frontend; the JSON sitemap API stays unchanged."""
from xml.etree.ElementTree import Element, SubElement, tostring

from django.http import HttpResponse
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from .models import Article, PublishingSettings


class NewsXmlSitemapView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        base = PublishingSettings.current().news_site_url.rstrip("/")
        root = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
        for path in ("", "/about", "/contact", "/privacy", "/disclaimer", "/ethics"):
            SubElement(SubElement(root, "url"), "loc").text = base + "/nobleseek" + path
        articles = Article.objects.filter(
            content_type=Article.ContentType.NEWS, status=Article.Status.PUBLISHED,
            published_at__lte=timezone.now()).only("slug", "content_type", "updated_at")
        for article in articles.iterator():
            node = SubElement(root, "url")
            SubElement(node, "loc").text = article.get_canonical_url(base)
            SubElement(node, "lastmod").text = article.updated_at.isoformat()
        response = HttpResponse(tostring(root, encoding="utf-8", xml_declaration=True),
                                content_type="application/xml")
        response["Cache-Control"] = "public, max-age=0, s-maxage=300, stale-while-revalidate=60"
        return response
