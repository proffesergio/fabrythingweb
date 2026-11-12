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


def blocks_html(blocks, products):
    """Safe semantic fallback: all text escaped, affiliate links explicitly labelled."""
    lookup = {p['id']: p for p in products}
    output = []
    for i, b in enumerate(blocks):
        kind = b['type']
        if kind in ('paragraph', 'heading', 'verdict'):
            tag = {'paragraph': 'p', 'heading': 'h2', 'verdict': 'aside'}[kind]
            output.append(f'<{tag} id="section-{i}">{escape(b["text"])}</{tag}>')
        elif kind in ('comparison', 'products'):
            output.append('<table><caption>Product comparison — check each website for the current price</caption><thead><tr><th scope="col">Product</th><th scope="col">Details</th></tr></thead><tbody>')
            for pid in b['productIds']:
                p = lookup[pid]
                details = '; '.join(f'{k}: {v}' for k, v in p.get('specs', {}).items())
                output.append(f'<tr><th scope="row"><a href="{escape(p["url"], quote=True)}" rel="nofollow sponsored noopener">{escape(p["title"])}</a></th><td>{escape(details)}</td></tr>')
                if p.get('review'):
                    review = p['review']
                    output.append('<tr><td colspan="2"><blockquote>' + escape(review['body']) + '</blockquote><p>Review by ' + escape(review['author']) + ' · ' + escape(str(review['datePublished'])) + ' · <a href="' + escape(review['sourceUrl'], quote=True) + '" rel="nofollow noopener">Review source</a></p></td></tr>')
            output.append('</tbody></table>')
        elif kind == 'pros_cons':
            for key in ('pros', 'cons'):
                output.append('<h3>' + key.replace('_', ' ').title() + '</h3><ul>' + ''.join('<li>' + escape(x) + '</li>' for x in b[key]) + '</ul>')
        elif kind == 'faq':
            output.extend('<h3>' + escape(x['question']) + '</h3><p>' + escape(x['answer']) + '</p>' for x in b['items'])
        elif kind == 'image' and b.get('src'):
            srcset = ', '.join(f'{v["src"]} {v["width"]}w' for v in b.get('variants', []))
            responsive = f' srcset="{escape(srcset, quote=True)}" sizes="(max-width: 800px) 100vw, 800px"' if srcset else ''
            output.append(f'<figure><img src="{escape(b["src"], quote=True)}" alt="{escape(b["alt"], quote=True)}" width="{b["width"]}" height="{b["height"]}" loading="lazy" decoding="async"{responsive}></figure>')
    return '\n'.join(output)
