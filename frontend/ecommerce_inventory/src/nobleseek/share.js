// Share-link builders for desk + portal. Pure functions (tested).

export function articleShareUrl(slug) {
  const origin = typeof window !== 'undefined' ? window.location.origin : '';
  return `${origin}/nobleseek/${slug || ''}`;
}

export function shareLinks(url, title = '') {
  const u = encodeURIComponent(url);
  const t = encodeURIComponent(title);
  return {
    facebook: `https://www.facebook.com/sharer/sharer.php?u=${u}`,
    x: `https://twitter.com/intent/tweet?text=${t}&url=${u}`,
    whatsapp: `https://wa.me/?text=${t}%20${u}`,
    telegram: `https://t.me/share/url?url=${u}&text=${t}`,
  };
}

/** Native sheet on phones, clipboard on desktop. Returns what happened. */
export async function nativeShareOrCopy({ title, text, url }) {
  try {
    if (typeof navigator !== 'undefined' && navigator.share) {
      await navigator.share({ title, text, url });
      return 'shared';
    }
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(url);
      return 'copied';
    }
  } catch { /* user dismissed or clipboard denied */ }
  return 'failed';
}
