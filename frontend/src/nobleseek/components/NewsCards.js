import React from 'react';
import { Box, Typography, Chip } from '@mui/material';
import { Link } from 'react-router-dom';
import { articleUrl } from '../api';
import { timeAgoBn } from '../bn';
import { NS_ACCENT } from '../portal/PortalHeader';

// Shared image block with branded gradient fallback (no photo → still looks
// like a designed newspaper card, never a broken-image icon).
export function NewsImage({ src, alt, ratio = '56.25%', radius = 2, eager = false }) {
  return (
    <Box sx={{ position: 'relative', paddingTop: ratio, bgcolor: '#1a1a1a', borderRadius: radius, overflow: 'hidden' }}>
      {src ? (
        <Box
          component="img" src={src} alt={alt || ''} loading={eager ? 'eager' : 'lazy'}
          {...(eager ? { fetchPriority: 'high' } : {})}
          sx={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }}
        />
      ) : (
        <Box sx={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg,#101244,#F2631F)', color: 'white', fontWeight: 900, fontSize: '1.5rem' }} className="ns-serif">
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

// Red-bar section title with "আরও" link — the newspaper section rhythm.
export function SectionHeader({ title, to, actionLabel = 'আরও' }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.2, mb: 2, mt: 5 }}>
      <Box sx={{ width: 5, height: 26, bgcolor: NS_ACCENT, borderRadius: 1 }} />
      <Typography variant="h5" fontWeight={900} className="ns-serif" sx={{ fontSize: '1.35rem' }}>{title}</Typography>
      <Box sx={{ flex: 1, height: 1, bgcolor: '#e5e5e5' }} />
      {to && (
        <Typography component={Link} to={to} variant="body2" fontWeight={700} sx={{ color: NS_ACCENT, textDecoration: 'none', whiteSpace: 'nowrap' }} className="ns-sans">
          {actionLabel} →
        </Typography>
      )}
    </Box>
  );
}

// Big overlay hero for the lead story.
export function LeadCard({ article, utm }) {
  if (!article) return null;
  return (
    <Box
      component={Link} to={articleUrl(article.slug, utm)}
      sx={{ position: 'relative', display: 'block', borderRadius: 3, overflow: 'hidden', textDecoration: 'none', minHeight: { xs: 300, md: 430 }, bgcolor: '#141414' }}
    >
      {article.hero_image ? (
        <Box component="img" src={article.hero_image} alt={article.hero_image_alt || article.headline} loading="eager" fetchPriority="high" sx={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }} />
      ) : (
        <Box sx={{ position: 'absolute', inset: 0, background: 'linear-gradient(135deg,#2a0709,#C1121F)' }} />
      )}
      <Box sx={{ position: 'absolute', inset: 0, background: 'linear-gradient(transparent 30%, rgba(0,0,0,0.88))' }} />
      <Box sx={{ position: 'absolute', bottom: 0, left: 0, right: 0, p: { xs: 2, md: 3 }, color: 'white' }}>
        <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
          {article.category_name && <Chip size="small" label={article.category_name} sx={{ bgcolor: NS_ACCENT, color: 'white', fontWeight: 700 }} />}
          {article.is_breaking && <Chip size="small" label="ব্রেকিং" sx={{ bgcolor: 'white', color: NS_ACCENT, fontWeight: 800 }} />}
        </Box>
        <Typography variant="h4" fontWeight={900} className="ns-serif ns-clamp-3" sx={{ lineHeight: 1.35, fontSize: { xs: '1.4rem', md: '2rem' } }}>
          {article.headline_bn || article.headline}
        </Typography>
        {article.excerpt && (
          <Typography variant="body2" className="ns-sans ns-clamp-2" sx={{ mt: 1, color: 'rgba(255,255,255,0.85)', display: { xs: 'none', sm: 'block' } }}>
            {article.excerpt}
          </Typography>
        )}
        <Box sx={{ mt: 1 }}><Meta article={article} light /></Box>
      </Box>
    </Box>
  );
}

// Standard card: image top, headline below.
export function SecondaryCard({ article, utm }) {
  if (!article) return null;
  return (
    <Box component={Link} to={articleUrl(article.slug, utm)} sx={{ textDecoration: 'none', color: 'inherit', display: 'block', height: '100%' }}>
      <NewsImage src={article.hero_image} alt={article.hero_image_alt || article.headline} />
      <Box sx={{ pt: 1 }}>
        {article.category_name && (
          <Typography variant="caption" fontWeight={800} sx={{ color: NS_ACCENT }} className="ns-sans">{article.category_name}</Typography>
        )}
        <Typography variant="subtitle1" fontWeight={800} className="ns-serif ns-clamp-3" sx={{ lineHeight: 1.5, fontSize: '1.02rem', mt: 0.25 }}>
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
    <Box component={Link} to={articleUrl(article.slug, utm)} sx={{ display: 'flex', gap: 1.5, textDecoration: 'none', color: 'inherit', py: 1.25, borderBottom: '1px solid #eee' }}>
      <Box sx={{ width: thumb, flexShrink: 0 }}>
        <NewsImage src={article.hero_image} alt={article.hero_image_alt || article.headline} ratio="75%" radius={1.5} />
      </Box>
      <Box sx={{ minWidth: 0 }}>
        <Typography variant="body2" fontWeight={700} className="ns-serif ns-clamp-3" sx={{ lineHeight: 1.55 }}>
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
    <Box component={Link} to={articleUrl(article.slug, utm)} sx={{ display: 'flex', gap: 1.5, textDecoration: 'none', color: 'inherit', py: 1.25, borderBottom: '1px solid #eee' }}>
      <Typography className="ns-serif" sx={{ fontSize: '1.9rem', fontWeight: 900, color: '#e3e3e3', lineHeight: 1, minWidth: 34 }}>
        {rank}
      </Typography>
      <Box sx={{ minWidth: 0 }}>
        <Typography variant="body2" fontWeight={700} className="ns-serif ns-clamp-3" sx={{ lineHeight: 1.55 }}>
          {article.headline_bn || article.headline}
        </Typography>
        <Box sx={{ mt: 0.5 }}><Meta article={article} /></Box>
      </Box>
    </Box>
  );
}
