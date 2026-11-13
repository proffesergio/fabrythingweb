"""Public HTML for all visitors, enhanced by the existing React store (no cloaking)."""

import json
from types import SimpleNamespace
from urllib.parse import quote, urlsplit

from catalog.models import Products
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils.html import strip_tags

ORIGIN = "https://www.fabrything.com"


def safe_image(item):
    url = (
        item
        if isinstance(item, str)
        else item.get("url", "")
        if isinstance(item, dict)
        else ""
    )
    if url.startswith("/api/media/"):
        return ORIGIN + url
    parsed = urlsplit(url)
    return (
        url
        if parsed.scheme == "https" and parsed.netloc and not parsed.username
        else ""
    )


def product_card(product):
    return {
        "name": product.name,
        "url": "/product/" + quote(product.slug, safe=""),
        "image": next(
            (safe_image(i) for i in product.image or [] if safe_image(i)), ""
        ),
        "price": product.discount_price or product.initial_selling_price,
    }


def store_document(request, kind="home", slug=None):
    queryset = (
        Products.objects.filter(status="ACTIVE")
        .exclude(slug="")
        .select_related("category_id")
    )
    context = {
        "origin": ORIGIN,
        "kind": kind,
        "noindex": False,
        "image": ORIGIN + "/fabrything-horizontal-light.png",
        "schema": "",
        "cards": [],
    }
    if slug:
        product = get_object_or_404(queryset.prefetch_related("variants"), slug=slug)
        path = "/product/" + quote(product.slug, safe="")
        card = product_card(product)
        description = strip_tags(product.description or "").strip()
        context.update(
            product=product,
            title=(product.name or product.sku) + " — Fabrything",
            description=description[:160]
            or "Explore product details and order online from Fabrything.",
            product_description=description,
            image=card["image"] or context["image"],
            card=card,
            highlights=[str(x) for x in product.highlights[:12]]
            if isinstance(product.highlights, list)
            else [],
            variants=[v for v in product.variants.all() if v.is_active],
            cards=[
                product_card(p)
                for p in queryset.filter(category_id=product.category_id)
                .exclude(pk=product.pk)
                .order_by("-created_at")[:6]
            ],
        )
        offers = [
            {
                "@type": "Offer",
                "sku": v.sku,
                "price": str(v.effective_price),
                "priceCurrency": "BDT",
                "url": ORIGIN + path,
                "availability": "https://schema.org/InStock"
                if v.in_stock
                else "https://schema.org/OutOfStock",
            }
            for v in context["variants"][:50]
        ]
        schema = {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "Product",
                    "@id": ORIGIN + path + "#product",
                    "name": product.name,
                    "description": description,
                    "sku": product.sku,
                    "url": ORIGIN + path,
                    **({"image": card["image"]} if card["image"] else {}),
                    **({"offers": offers} if offers else {}),
                },
                {
                    "@type": "BreadcrumbList",
                    "itemListElement": [
                        {
                            "@type": "ListItem",
                            "position": 1,
                            "name": "Shop",
                            "item": ORIGIN + "/shop",
                        },
                        {
                            "@type": "ListItem",
                            "position": 2,
                            "name": product.name,
                            "item": ORIGIN + path,
                        },
                    ],
                },
            ],
        }
    elif kind == "deals":
        from .models import AffiliateProduct

        path = "/deals"
        context.update(
            title="Product Deals — Fabrything",
            heading="Current partner deals",
            description="Explore current product deals and partner offers at Fabrything.",
            affiliate=True,
            cards=[
                {
                    "name": a.title,
                    "url": "/api/store/partner-picks/" + str(a.pk) + "/r/",
                    "image": safe_image(a.image),
                    "price": a.current_price or a.original_price,
                    "affiliate": True,
                }
                for a in AffiliateProduct.objects.for_deals_page()[:100]
            ],
        )
        schema = {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "name": context["title"],
            "url": ORIGIN + path,
        }
    else:
        path = "/" if kind == "home" else "/" + kind
        if kind not in ("home", "shop", "deals"):
            raise Http404()
        try:
            page = int(request.GET.get("page", "1")) if kind == "shop" else 1
            if page < 1 or page > 10000:
                raise ValueError()
        except ValueError:
            raise Http404("Invalid page")
        params = request.GET.copy()
        if kind == "home":
            params.clear()
        if params.get("q") and not params.get("search"):
            params["search"] = params["q"][:120]
        import math

        for field in ("price_min", "price_max"):
            if params.get(field):
                try:
                    if (
                        not math.isfinite(float(params[field]))
                        or float(params[field]) < 0
                    ):
                        raise ValueError()
                except ValueError:
                    raise Http404("Invalid price filter")
        from .views import PublicProductListView

        view = PublicProductListView()
        view.request = SimpleNamespace(query_params=params)
        queryset = view.get_queryset().exclude(slug="")
        context["noindex"] = any(key != "page" for key in params)
        batch = list(queryset[(page - 1) * 12 : page * 12 + 1])
        if page > 1 and not batch:
            raise Http404("Page not found")

        def page_url(number):
            values = params.copy()
            values["page"] = number
            return path + "?" + values.urlencode()

        context.update(
            cards=[product_card(p) for p in batch[:12]],
            title={
                "home": "Fabrything — Fashion, lifestyle & everyday essentials",
                "shop": "Shop products — Fabrything",
                "deals": "Latest product deals — Fabrything",
            }[kind],
            description="Discover fashion, lifestyle and everyday essentials from Fabrything. Explore product details, current prices and cash-on-delivery shopping in Bangladesh.",
            heading={
                "home": "Discover your everyday favourites.",
                "shop": "Shop our collection",
                "deals": "Latest deals",
            }[kind],
            previous=page_url(page - 1) if page > 1 else None,
            following=page_url(page + 1)
            if kind == "shop" and len(batch) > 12
            else None,
        )
        if page > 1:
            path += "?page=" + str(page)
        schema = {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "name": context["title"],
            "url": ORIGIN + path,
        }
    context["canonical"] = ORIGIN + path
    context["schema"] = (
        json.dumps(schema, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    response = render(request, "storefront/store_document.html", context)
    response["Cache-Control"] = (
        "public, max-age=0, s-maxage=60, stale-while-revalidate=30"
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response
