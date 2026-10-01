import React from 'react';
import { Box, Card, CardMedia, CardContent, Typography, Chip, Skeleton } from '@mui/material';
import { Link } from 'react-router-dom';
import { timeAgo, articleUrl } from '../api';

export function NewsCardSkeleton() {
  return (
    <Card sx={{ borderRadius: 3, overflow: 'hidden' }}>
      <Skeleton variant="rectangular" height={180} />
      <CardContent>
        <Skeleton width="40%" /><Skeleton width="90%" /><Skeleton width="70%" />
      </CardContent>
    </Card>
  );
}

// Modern fast card: webp-friendly img, category badge, time-ago + read time.
export default function NewsCard({ article, utm }) {
  if (!article) return null;
  const url = articleUrl(article.slug, utm || article.utm_campaign);
  return (
    <Card
      component={Link}
      to={url}
      sx={{
        borderRadius: 3, overflow: 'hidden', textDecoration: 'none', height: '100%',
        display: 'flex', flexDirection: 'column',
        transition: 'transform .2s ease, box-shadow .2s ease',
        '&:hover': { transform: 'translateY(-3px)', boxShadow: 6 },
      }}
    >
      <Box sx={{ position: 'relative', paddingTop: '56.25%', bgcolor: '#0f172a' }}>
        {article.hero_image ? (
          <CardMedia
            component="img"
            image={article.hero_image}
            alt={article.hero_image_alt || article.headline}
            loading="lazy"
            sx={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }}
          />
        ) : (
          <Box sx={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg,#0f172a,#4c1d95)', color: 'white', fontWeight: 800, fontSize: '1.6rem', px: 2, textAlign: 'center' }}>
            NobleSeek
          </Box>
        )}
        <Box sx={{ position: 'absolute', top: 8, left: 8, display: 'flex', gap: 0.5 }}>
          {article.category_name && <Chip size="small" label={article.category_name} color="secondary" sx={{ fontWeight: 700 }} />}
          {article.is_breaking && <Chip size="small" label="BREAKING" color="error" sx={{ fontWeight: 800 }} />}
        </Box>
      </Box>
      <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 0.75 }}>
        <Typography variant="subtitle1" fontWeight={800} sx={{ lineHeight: 1.35, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
          {article.headline_bn || article.headline}
        </Typography>
        {article.excerpt && (
          <Typography variant="body2" color="text.secondary" sx={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
            {article.excerpt}
          </Typography>
        )}
        <Box sx={{ mt: 'auto', pt: 1, display: 'flex', gap: 1, alignItems: 'center' }}>
          <Typography variant="caption" color="text.secondary">{timeAgo(article.published_at || article.created_at)}</Typography>
          <Typography variant="caption" color="text.secondary">•</Typography>
          <Typography variant="caption" color="text.secondary">{article.read_time_minutes || 3} min read</Typography>
          <Typography variant="caption" color="text.secondary">•</Typography>
          <Typography variant="caption" color="text.secondary">{article.view_count || 0} views</Typography>
        </Box>
      </CardContent>
    </Card>
  );
}
