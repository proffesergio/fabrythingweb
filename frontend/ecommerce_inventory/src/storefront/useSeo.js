import { useEffect } from 'react';

export default function useSeo({ title, description, path, noindex = false }) {
    useEffect(() => {
        if (!title) return;
        document.title = title;
        const url = `https://www.fabrything.com${path}`;
        const meta = (attribute, key, value) => {
            let node = document.querySelector(`meta[${attribute}="${key}"]`);
            if (!node) {
                node = document.createElement('meta');
                node.setAttribute(attribute, key);
                document.head.appendChild(node);
            }
            node.content = value;
        };
        meta('name', 'description', description);
        meta('name', 'robots', noindex ? 'noindex,follow' : 'index,follow');
        meta('property', 'og:title', title);
        meta('property', 'og:description', description);
        meta('property', 'og:url', url);
        meta('property', 'og:type', 'website');
        let canonical = document.querySelector('link[rel="canonical"]');
        if (!canonical) {
            canonical = document.createElement('link');
            canonical.rel = 'canonical';
            document.head.appendChild(canonical);
        }
        canonical.href = url;
        return () => meta('name', 'robots', 'index,follow');
    }, [title, description, path, noindex]);
}
