"""Public journal projection and metadata shared by API, HTML and JSON-LD."""
from html import escape
import re
from .journal_models import JournalArticle

ORIGIN = 'https://www.fabrything.com'


def cluster_path(cluster):
    result, seen = [], set()
    while cluster and cluster.pk not in seen and len(result) < 5:
        seen.add(cluster.pk)
        result.insert(0, {'name': cluster.name, 'slug': cluster.slug, 'level': cluster.level})
        cluster = cluster.parent
    return result


def journal_data(article):
    try:
        j = article.journal
    except JournalArticle.DoesNotExist:
        return None
    # An editor's legacy HTML correction must win over an older structured mirror.
    from nobleseek.sanitization import sanitize_article_html
    if sanitize_article_html(blocks_html(j.blocks, j.products)) != sanitize_article_html(article.body_html):
        return None
    return {'version': 'fabrything-journal-v1', 'intent': j.intent,
            'problem': j.problem, 'audience': j.audience, 'keyword': j.keyword,
            'cluster': cluster_path(j.cluster), 'blocks': j.blocks,
            'products': j.products, 'sources': j.sources,
            'disclosure': 'This guide may contain affiliate links. We may earn a commission if you buy through them. Fabrything store links lead to our own products. Check the destination website for the current price.',
            'editorial': {'reviewed': j.editorial.get('reviewed') is True}}


def journal_json_ld(article):
    data = journal_data(article)
    url = article.get_canonical_url()
    graph = [{'@type': 'Article', '@id': url + '#article', 'headline': article.effective_headline,
              'description': article.seo_description or article.excerpt,
              'mainEntityOfPage': url,
              'inLanguage': 'bn' if re.search(r'[\u0980-\u09ff]', article.headline) else 'en',
              'author': {'@type': 'Organization', 'name': 'Fabrything Editorial', 'url': ORIGIN + '/about'},
              'publisher': {'@type': 'Organization', 'name': 'Fabrything', 'url': ORIGIN},
              'datePublished': article.published_at.isoformat() if article.published_at else None,
              'dateModified': article.updated_at.isoformat()}]
    if article.hero_image:
        graph[0]['image'] = article.hero_image
    trail = [{'name': 'Home', 'item': ORIGIN}, {'name': 'Journal', 'item': ORIGIN + '/blog'}]
    if data:
        trail.extend({'name': c['name'], 'item': ORIGIN + '/blog/topic/' + c['slug']} for c in data['cluster'])
        visible_products = {pid for b in data['blocks'] for pid in b.get('productIds', [])}
        for product in data['products']:
            if product['id'] not in visible_products:
                continue
            p = {'@type': 'Product', '@id': url + '#product-' + product['id'], 'name': product['title'], 'url': product['url']}
            if product.get('image'):
                p['image'] = product['image']
            if product.get('review'):
                r = product['review']
                p['review'] = {'@type': 'Review', 'author': {'@type': 'Person', 'name': r['author']},
                               'reviewBody': r['body'], 'datePublished': str(r['datePublished']), 'url': r['sourceUrl']}
            graph.append(p)
        faqs = [x for b in data['blocks'] if b['type'] == 'faq' for x in b['items']]
        if faqs:
            graph.append({'@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': x['question'], 'acceptedAnswer': {'@type': 'Answer', 'text': x['answer']}} for x in faqs]})
    trail.append({'name': article.effective_headline, 'item': url})
    graph.append({'@type': 'BreadcrumbList', 'itemListElement': [{'@type': 'ListItem', 'position': i + 1, **x} for i, x in enumerate(trail)]})
    return {'@context': 'https://schema.org', '@graph': graph}


def guide_contents(blocks):
    labels = {'verdict': 'Quick verdict', 'comparison': 'Compare your options', 'products': 'Products in this guide', 'pros_cons': 'The trade-offs', 'faq': 'Common questions'}
    return [{'index': i, 'title': b.get('text') if b['type'] == 'heading' else labels[b['type']]} for i, b in enumerate(blocks) if b['type'] == 'heading' or b['type'] in labels]


def blocks_html(blocks, products):
    """Autoescaped reusable blocks, shared with canonical HTML and the stored mirror."""
    from django.template.loader import render_to_string
    from nobleseek.sanitization import sanitize_article_html
    lookup = {p['id']: p for p in products}
    prepared, image_seen = [], False
    for block in blocks:
        b = dict(block)
        b['selected'] = [lookup[pid] for pid in b.get('productIds', []) if pid in lookup]
        if b['type'] == 'image' and b.get('src'):
            b['srcset'] = ', '.join(f'{v["src"]} {v["width"]}w' for v in b.get('variants', []))
            b['priority'] = not image_seen
            image_seen = True
        prepared.append(b)
    return sanitize_article_html(render_to_string('storefront/journal_blocks.html', {'blocks': prepared}))
