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
               "tr", "th", "td"}
    for tag in soup.find_all(True):
        if tag.name not in allowed:
            tag.unwrap()
            continue
        attrs = {}
        for key in ("alt", "title"):
            if key in tag.attrs:
                attrs[key] = tag.attrs[key]
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
