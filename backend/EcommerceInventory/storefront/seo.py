from urllib.parse import quote
from xml.etree.ElementTree import Element, SubElement, tostring

from django.http import HttpResponse
from django.utils import timezone
from catalog.models import Products
from nobleseek.models import Article


def sitemap(request):
    """Current public URLs; newly published products need no frontend rebuild."""
    root = Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    paths = ['/', '/shop', '/deals', '/custom-printing', '/food',
             '/food/restaurants', '/food/partner', '/about', '/privacy',
             '/terms', '/shipping', '/nobleseek', '/nobleseek/about',
             '/nobleseek/contact', '/nobleseek/privacy', '/nobleseek/disclaimer',
             '/nobleseek/ethics']
    paths.extend('/product/' + quote(slug, safe='') for slug in
                 Products.objects.filter(status='ACTIVE').exclude(slug='').values_list('slug', flat=True))
    paths.extend('/nobleseek/' + quote(slug, safe='') for slug in
                 Article.objects.filter(status=Article.Status.PUBLISHED,
                                        published_at__lte=timezone.now()).values_list('slug', flat=True))
    for path in paths:
        SubElement(SubElement(root, 'url'), 'loc').text = 'https://www.fabrything.com' + path
    response = HttpResponse(tostring(root, encoding='utf-8', xml_declaration=True), content_type='application/xml')
    response['Cache-Control'] = 'public, max-age=0, s-maxage=300, stale-while-revalidate=60'
    return response
