import React, { useState } from 'react';
import { Box, IconButton, Tooltip, Snackbar } from '@mui/material';
import { Facebook, X, WhatsApp, Link as LinkIcon } from '@mui/icons-material';

// Sticky share rail — drives FB NobleSeek page <-> site loop.
export default function ShareBar({ title, vertical = false }) {
  const [copied, setCopied] = useState(false);
  const url = typeof window !== 'undefined' ? window.location.href : '';
  const text = `${title || 'NobleSeek'} — NobleSeek by Fabrything`;
  const links = [
    { icon: <Facebook />, label: 'Share on Facebook', href: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}` },
    { icon: <X />, label: 'Share on X', href: `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}` },
    { icon: <WhatsApp />, label: 'Share on WhatsApp', href: `https://wa.me/?text=${encodeURIComponent(`${text} ${url}`)}` },
  ];
  return (
    <Box sx={{ display: 'flex', flexDirection: vertical ? 'column' : 'row', gap: 0.5, alignItems: 'center' }}>
      {links.map((l) => (
        <Tooltip key={l.label} title={l.label}>
          <IconButton component="a" href={l.href} target="_blank" rel="noopener noreferrer" size="small" sx={{ border: '1px solid', borderColor: 'divider' }}>
            {l.icon}
          </IconButton>
        </Tooltip>
      ))}
      <Tooltip title="Copy link">
        <IconButton size="small" sx={{ border: '1px solid', borderColor: 'divider' }} onClick={async () => {
          try { await navigator.clipboard.writeText(url); } catch {}
          setCopied(true);
        }}>
          <LinkIcon />
        </IconButton>
      </Tooltip>
      <Snackbar open={copied} autoHideDuration={1800} onClose={() => setCopied(false)} message="Link copied" />
    </Box>
  );
}

export function FacebookComments({ href }) {
  const url = href || (typeof window !== 'undefined' ? window.location.href : '');
  return (
    <Box sx={{ mt: 4 }}>
      <div className="fb-comments" data-href={url} data-width="100%" data-numposts="5" />
      <Box component="p" sx={{ fontSize: 12, color: 'text.secondary' }}>
        Comments load via Facebook SDK. Add your FB App ID in index.html to enable.
      </Box>
    </Box>
  );
}
