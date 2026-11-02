import React, { useEffect } from 'react';

// Sets <title>, meta description, OG/Twitter tags + JSON-LD NewsArticle.
// Also swaps the browser-tab icon to the NobleSeek badge while a news route
// is mounted (restored on unmount so shop keeps its own favicon).
export default function NewsSeo({ title, description, image, slug, jsonLd, publishedAt }) {
  useEffect(() => {
    const site = window.location.origin;
    const url = `${site}/nobleseek/${slug || ''}`;
    document.title = title ? `${title} — নোবেলসিক` : 'নোবেলসিক — সর্বশেষ সংবাদ';
    const setMeta = (attr, key, content) => {
      if (!content) return;
      let el = document.querySelector(`meta[${attr}="${key}"]`);
      if (!el) { el = document.createElement('meta'); el.setAttribute(attr, key); document.head.appendChild(el); }
      el.setAttribute('content', content);
    };
    setMeta('name', 'description', description);
    setMeta('property', 'og:type', 'article');
    setMeta('property', 'og:title', title);
    setMeta('property', 'og:description', description);
    setMeta('property', 'og:image', image);
    setMeta('property', 'og:url', url);
    setMeta('name', 'twitter:card', 'summary_large_image');
    let link = document.querySelector('link[rel="canonical"]');
    if (!link) { link = document.createElement('link'); link.rel = 'canonical'; document.head.appendChild(link); }
    link.href = url;
    let ld = document.getElementById('ns-jsonld');
    if (jsonLd) {
      if (!ld) { ld = document.createElement('script'); ld.id = 'ns-jsonld'; ld.type = 'application/ld+json'; document.head.appendChild(ld); }
      ld.textContent = JSON.stringify(jsonLd);
    }
    // News-tab icon: the NobleSeek badge (square mark PNG), restored on unmount.
    const iconLink = document.querySelector('link[rel="icon"]');
    const prevIcon = iconLink?.getAttribute('href') || null;
    let nsIcon = null;
    try {
      nsIcon = document.createElement('link');
      nsIcon.rel = 'icon';
      nsIcon.type = 'image/png';
      nsIcon.href = '/nobleseek-mark.png';
      document.head.appendChild(nsIcon);
    } catch { nsIcon = null; }
    return () => {
      if (ld) ld.textContent = '';
      if (nsIcon) nsIcon.remove();
      if (iconLink && prevIcon) iconLink.setAttribute('href', prevIcon);
    };
  }, [title, description, image, slug, jsonLd, publishedAt]);
  return null;
}
