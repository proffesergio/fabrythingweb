import React, { useState } from 'react';
import { Box, Typography } from '@mui/material';
import { Link } from 'react-router-dom';
import { articleUrl } from '../api';
import { timeAgoBn, toBn } from '../bn';
import { NS_ACCENT } from '../portal/PortalHeader';

// Neutral branded fallback for missing or failed API images.
export function NewsImage({ src, alt, ratio = '56.25%', radius = 0, eager = false }) {
  const [failedSrc, setFailedSrc] = useState(null);
  return (
    <Box sx={{ position: 'relative', paddingTop: ratio, bgcolor: '#F2F2F2', borderRadius: radius, overflow: 'hidden' }}>
      {src && failedSrc !== src ? (
        <Box
          component="img" src={src} onError={() => setFailedSrc(src)} alt={alt || ''} loading={eager ? 'eager' : 'lazy'}
          {...(eager ? { fetchpriority: 'high' } : {})}
          sx={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }}
        />
      ) : (
        <Box sx={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#F2F2F2', color: '#101244', fontWeight: 900, fontSize: '1.5rem' }} className="ns-serif">
          নোবেলসিক
        </Box>
      )}
    </Box>
  );
}

function Meta({ article, light = false }) {
  return (
    <Typography variant="caption" sx={{ color: light ? 'rgba(255,255,255,0.85)' : 'text.secondary' }} className="ns-sans">
      {timeAgoBn(article.published_at || article.created_at)}
    </Typography>
  );
}

// Flat section rule from the approved editorial layout.
export function SectionHeader({ title, to, actionLabel = 'আরও' }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, pb: 1, mb: 3, mt: 4, borderBottom: '1px solid #101244' }}>
      <Box aria-hidden="true" sx={{ width: 6, height: 24, bgcolor: NS_ACCENT, flexShrink: 0 }} />
      <Typography component="h2" fontWeight={800} className="ns-serif" sx={{ color: '#040D33', fontSize: '1.5rem', flex: 1, minWidth: 0 }}>{title}</Typography>
      {to && <Typography component={Link} to={to} fontWeight={700} sx={{ color: NS_ACCENT, textDecoration: 'none', flexShrink: 0, '&:hover': { textDecoration: 'underline' } }} className="ns-sans">{actionLabel} →</Typography>}
    </Box>
  );
}

export function LeadCard({ article, utm }) {
  if (!article) return null;
  return (
    <Box component={Link} to={articleUrl(article.slug, utm)} sx={{ display: 'block', color: '#040D33', textDecoration: 'none', overflowWrap: 'anywhere', '&:hover h1': { color: NS_ACCENT } }}>
      <NewsImage src={article.hero_image} alt={article.hero_image_alt || ''} ratio="62.5%" eager />
      <Box sx={{ pt: 2 }}>
        {(article.category_name || article.is_breaking) && <Typography className="ns-sans" sx={{ color: NS_ACCENT, fontWeight: 700, mb: 1 }}>{article.category_name}{article.is_breaking && ' · ব্রেকিং'}</Typography>}
        <Typography component="h1" className="ns-serif" fontWeight={800} sx={{ fontSize: { xs: '2rem', md: '2.375rem' }, lineHeight: 1.25 }}>{article.headline_bn || article.headline}</Typography>
        {article.excerpt && <Typography className="ns-serif ns-clamp-3" sx={{ mt: 1.5, mb: 2, fontSize: 18, lineHeight: 1.6, color: '#28303B' }}>{article.excerpt}</Typography>}
        <Box sx={{ mt: 1 }}><Meta article={article} /></Box>
      </Box>
    </Box>
  );
}

// Standard card: image top, headline below.
export function SecondaryCard({ article, utm, heading = 'h3' }) {
  if (!article) return null;
  return (
    <Box component={Link} to={articleUrl(article.slug, utm)} sx={{ textDecoration: 'none', display: 'block', height: '100%', overflowWrap: 'anywhere', color: '#040D33', '&:hover h2, &:hover h3': { color: NS_ACCENT } }}>
      <NewsImage src={article.hero_image} alt={article.hero_image_alt || ''} ratio="62.5%" />
      <Box sx={{ pt: 1 }}>
        {article.category_name && (
          <Typography variant="caption" fontWeight={800} sx={{ color: NS_ACCENT }} className="ns-sans">{article.category_name}</Typography>
        )}
        <Typography component={heading} variant="subtitle1" fontWeight={800} className="ns-serif ns-clamp-3" sx={{ lineHeight: 1.4, fontSize: heading === 'h2' ? '1.375rem' : '1.25rem', mt: 0.25 }}>
          {article.headline_bn || article.headline}
        </Typography>
        <Box sx={{ mt: 0.5 }}><Meta article={article} /></Box>
      </Box>
    </Box>
  );
}

// Thumb-left row for section lists and sidebars.
export function HorizontalCard({ article, thumb = 112, utm }) {
  if (!article) return null;
  return (
    <Box component={Link} to={articleUrl(article.slug, utm)} sx={{ display: 'flex', gap: 1.5, textDecoration: 'none', color: 'inherit', py: 1.25, borderBottom: '1px solid #E8E8E8', overflowWrap: 'anywhere' }}>
      <Box sx={{ width: thumb, flexShrink: 0 }}>
        <NewsImage src={article.hero_image} alt={article.hero_image_alt || article.headline} ratio="75%" radius={0} />
      </Box>
      <Box sx={{ minWidth: 0 }}>
        <Typography component="h3" variant="body2" fontWeight={700} className="ns-serif ns-clamp-3" sx={{ lineHeight: 1.55 }}>
          {article.headline_bn || article.headline}
        </Typography>
        <Box sx={{ mt: 0.5 }}><Meta article={article} /></Box>
      </Box>
    </Box>
  );
}

// Ranked text item for সর্বাধিক পঠিত.
export function TextOnlyItem({ article, rank, utm }) {
  if (!article) return null;
  return (
    <Box component={Link} to={articleUrl(article.slug, utm)} sx={{ display: 'flex', gap: 1.5, textDecoration: 'none', color: 'inherit', py: 1.25, borderBottom: '1px solid #E8E8E8', overflowWrap: 'anywhere' }}>
      <Typography className="ns-serif" sx={{ fontSize: '1.9rem', fontWeight: 900, color: '#a4a9b4', lineHeight: 1, minWidth: 34 }}>
        {toBn(rank)}
      </Typography>
      <Box sx={{ minWidth: 0 }}>
        <Typography component="h3" variant="body2" fontWeight={700} className="ns-serif ns-clamp-3" sx={{ lineHeight: 1.55 }}>
          {article.headline_bn || article.headline}
        </Typography>
        <Box sx={{ mt: 0.5 }}><Meta article={article} /></Box>
      </Box>
    </Box>
  );
}
