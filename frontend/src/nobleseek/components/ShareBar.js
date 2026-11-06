import React, { useEffect, useState } from 'react';
import { Box, IconButton, Tooltip, Snackbar } from '@mui/material';
import { Facebook, X, WhatsApp, Link as LinkIcon } from '@mui/icons-material';

function getShareUrl(url) {
  const currentUrl = typeof window !== 'undefined' ? window.location.href : '';
  const canonical = typeof document !== 'undefined'
    ? document.querySelector('link[rel="canonical"]')?.getAttribute('href') : '';
  for (const candidate of [url, canonical, currentUrl]) {
    if (!candidate) continue;
    try {
      const cleanUrl = new URL(candidate, currentUrl || undefined);
      if (!['https:', 'http:'].includes(cleanUrl.protocol)) continue;
      cleanUrl.search = '';
      cleanUrl.hash = '';
      return cleanUrl.href;
    } catch {
      // Try the next source if this URL is invalid.
    }
  }
  return '';
}

export default function ShareBar({ title, vertical = false, url }) {
  const [copyMessage, setCopyMessage] = useState('');
  const [shareUrl, setShareUrl] = useState(() => getShareUrl(url));
  useEffect(() => {
    // Page SEO components may publish the canonical URL in a sibling effect.
    setShareUrl(getShareUrl(url));
  }, [url, title]);
  const text = `${title || 'নোবেলসিক'} — নোবেলসিক`;
  const links = [
    { icon: <Facebook />, label: 'Share on Facebook', href: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}` },
    { icon: <X />, label: 'Share on X', href: `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(shareUrl)}` },
    { icon: <WhatsApp />, label: 'Share on WhatsApp', href: `https://wa.me/?text=${encodeURIComponent(`${text} ${shareUrl}`)}` },
  ];
  return (
    <Box sx={{ display: 'flex', flexDirection: vertical ? 'column' : 'row', gap: 0.5, alignItems: 'center' }}>
      {links.map((l) => (
        <Tooltip key={l.label} title={l.label}>
          <IconButton component="a" aria-label={l.label} href={l.href} target="_blank" rel="noopener noreferrer" size="small" sx={{ border: '1px solid', borderColor: 'divider' }}>
            {l.icon}
          </IconButton>
        </Tooltip>
      ))}
      <Tooltip title="Copy link">
        <IconButton aria-label="Copy link" size="small" sx={{ border: '1px solid', borderColor: 'divider' }} onClick={async () => {
          setCopyMessage('');
          try {
            await navigator.clipboard.writeText(getShareUrl(url));
            setCopyMessage('Link copied');
          } catch {
            setCopyMessage('Could not copy link. Please try again.');
          }
        }}>
          <LinkIcon />
        </IconButton>
      </Tooltip>
      <Snackbar open={Boolean(copyMessage)} autoHideDuration={1800} onClose={() => setCopyMessage('')} message={copyMessage} />
    </Box>
  );
}

export function FacebookComments({ href }) {
  const url = href || (typeof window !== 'undefined' ? window.location.href : '');
  return (
    <Box sx={{ mt: 4 }}>
      <div className="fb-comments" data-href={url} data-width="100%" data-numposts="5" />
    </Box>
  );
}
