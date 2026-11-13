"""Conservative rich-text allowlist using the existing BeautifulSoup dependency."""
import re
from urllib.parse import urlsplit

from bs4 import BeautifulSoup, Comment


def sanitize_article_html(value):
    soup = BeautifulSoup(value, "html.parser")
    for comment in soup.find_all(string=lambda node: isinstance(node, Comment)):
        comment.extract()
    for tag in soup.find_all(["script", "style", "iframe", "object", "embed",
                              "svg", "math", "template", "form"]):
        tag.decompose()
    allowed = {"p", "br", "h2", "h3", "h4", "strong", "b", "em", "i", "u",
               "s", "blockquote", "ul", "ol", "li", "a", "img", "figure",
               "figcaption", "pre", "code", "hr", "table", "thead", "tbody",
               "tr", "th", "td", "caption", "aside", "section", "article", "div", "span", "dl", "dt", "dd", "cite", "details", "summary"}
    for tag in soup.find_all(True):
        if tag.name not in allowed:
            tag.unwrap()
            continue
        attrs = {}
        for key in ("alt", "title"):
            if key in tag.attrs:
                attrs[key] = tag.attrs[key]
        classes = tag.get('class', [])
        safe_classes = {'journal-verdict', 'journal-eyebrow', 'journal-tradeoffs', 'journal-faq', 'journal-image', 'journal-image-plan', 'journal-products', 'journal-product-card', 'journal-cta', 'journal-caption', 'journal-table-wrap'}
        kept = [c for c in classes if c in safe_classes]
        if kept:
            attrs['class'] = ' '.join(kept)
        if tag.name == 'div' and tag.get('role') == 'region' and tag.get('aria-label') == 'Product comparison':
            attrs.update({'role': 'region', 'aria-label': 'Product comparison', 'tabindex': '0'})
        if re.fullmatch(r'section-\d+', str(tag.get('id', ''))):
            attrs['id'] = tag['id']
        if tag.name in {'th', 'td'} and tag.get('scope') in {'row', 'col'}:
            attrs['scope'] = tag['scope']
        if tag.name in {'th', 'td'} and str(tag.get('colspan', '')).isdigit() and 1 <= int(tag['colspan']) <= 12:
            attrs['colspan'] = str(tag['colspan'])
        if tag.name == 'a':
            rel = tag.get('rel', [])
            if isinstance(rel, str):
                rel = rel.split()
            attrs['rel'] = ' '.join(sorted(set(rel) & {'nofollow', 'sponsored', 'noopener', 'noreferrer'} | {'noopener'}))
        if tag.name == 'img':
            srcset = str(tag.get('srcset', ''))
            if srcset and len(srcset) <= 8500 and all(re.fullmatch(r'https://[^\s,]+\s[1-4]?\d{2,3}w', x.strip()) for x in srcset.split(',')):
                attrs['srcset'] = srcset
                attrs['sizes'] = '(max-width: 800px) 100vw, 800px'
            for key in ('width', 'height'):
                if str(tag.get(key, '')).isdigit() and 1 <= int(tag[key]) <= 4000:
                    attrs[key] = str(tag[key])
            if tag.get('loading') in ('lazy', 'eager'):
                attrs['loading'] = tag['loading']
            attrs['decoding'] = 'async'
            if tag.get('fetchpriority') == 'high':
                attrs['fetchpriority'] = 'high'
        url_attr = "href" if tag.name == "a" else "src" if tag.name == "img" else None
        if url_attr and isinstance(tag.get(url_attr), str):
            url = tag[url_attr].strip()
            normalized = re.sub(r"[\x00-\x20\x7f]", "", url)
            schemes = {"http", "https", "mailto", "tel"} if tag.name == "a" else {"http", "https"}
            try:
                scheme = urlsplit(normalized).scheme.lower()
            except ValueError:
                scheme = None
            if scheme is not None and (scheme in schemes or (
                    not scheme and not normalized.startswith(("//", "\\")))):
                attrs[url_attr] = url
        tag.attrs = attrs
    return str(soup)
