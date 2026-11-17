"""News HTML for readers and crawlers, enhanced by the existing React portal."""
import json
from urllib.parse import urlencode

from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import Article, FlatPage, NewsCategory, PublishingSettings
from .sanitization import sanitize_article_html

ADSENSE_CLIENT = "ca-pub-1712742966437949"
INFO_TITLES = {
    "about": "আমাদের সম্পর্কে", "contact": "যোগাযোগ", "privacy": "গোপনীয়তা নীতি",
    "disclaimer": "ডিসক্লেইমার", "ethics": "সম্পাদকীয় নীতি",
}


def visible_news():
    return Article.objects.filter(content_type="NEWS", status="PUBLISHED", published_at__lte=timezone.now())


def news_document(request, slug=None):
    base = PublishingSettings.current().news_site_url.rstrip("/")
    context = {"base": base, "adsense_client": ADSENSE_CLIENT, "language": "bn",
               "title": "সর্বশেষ সংবাদ", "description": "নোবেলসিক — দেশ-বিদেশের সর্বশেষ সংবাদ, বিশ্লেষণ ও মতামত।",
               "canonical": base + "/nobleseek", "noindex": False,
               "image": base + "/nobleseek-mark.png", "schema": "{}"}
    if slug in INFO_TITLES:
        page = FlatPage.objects.filter(slug=slug, is_active=True).first()
        context.update(title=page.title if page else INFO_TITLES[slug],
                       description=page.intro if page else INFO_TITLES[slug],
                       canonical=base + "/nobleseek/" + slug,
                       info_page=slug, body=sanitize_article_html(page.body_html) if page else "")
    elif slug:
        article = get_object_or_404(visible_news().select_related("category"), slug=slug)
        image = article.hero_image
        if image.startswith("/"):
            image = base + image
        schema = article.get_json_ld(base)
        schema["headline"] = article.effective_headline
        schema["image"] = [image] if image else []
        schema["author"]["url"] = base + "/nobleseek/about"
        schema["publisher"]["logo"]["url"] = base + "/nobleseek-mark.png"
        context.update(article=article, title=article.seo_title or article.effective_headline,
                       description=article.seo_description or article.excerpt,
                       canonical=article.get_canonical_url(base), image=image or context["image"],
                       body=sanitize_article_html(article.body_html),
                       schema=json.dumps(schema, ensure_ascii=False).replace("<", "\\u003c"),
                       related=visible_news().exclude(pk=article.pk).filter(category=article.category)[:4])
    else:
        qs = visible_news().select_related("category").order_by("-published_at", "-pk")
        category = request.GET.get("category", "")
        search = request.GET.get("search", "").strip()[:120]
        if category:
            section = get_object_or_404(NewsCategory, slug=category, is_active=True)
            qs = qs.filter(category=section)
            context.update(title=section.name, description=section.description or section.name)
        if search:
            qs = qs.filter(Q(headline__icontains=search) | Q(headline_bn__icontains=search) | Q(excerpt__icontains=search))
        try:
            page = int(request.GET.get("page", "1"))
            if not 1 <= page <= 10000:
                raise ValueError
        except ValueError:
            raise Http404("Invalid page")
        batch = list(qs[(page - 1) * 12:page * 12 + 1])
        if page > 1 and not batch:
            raise Http404("Page not found")
        def page_url(number):
            params = {"page": number} if number > 1 else {}
            if category:
                params["category"] = category
            if search:
                params["search"] = search
            return base + "/nobleseek" + ("?" + urlencode(params) if params else "")
        context.update(articles=batch[:12], canonical=page_url(page), noindex=bool(search) or not batch,
                       previous=page_url(page - 1) if page > 1 else None,
                       following=page_url(page + 1) if len(batch) > 12 else None,
                       categories=NewsCategory.objects.filter(is_active=True, articles__in=visible_news()).distinct())
    response = render(request, "nobleseek/document.html", context)
    response["Cache-Control"] = "public, max-age=0, s-maxage=300, stale-while-revalidate=60"
    response["X-Content-Type-Options"] = "nosniff"
    return response
