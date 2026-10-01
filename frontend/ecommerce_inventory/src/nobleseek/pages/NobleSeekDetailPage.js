import React, { useEffect, useState } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import { Box, Container, Typography, Chip, Grid, Skeleton, Divider, Button } from '@mui/material';
import { fetchNewsDetail } from '../api';
import NewsSeo from '../components/NewsSeo';
import ShareBar, { FacebookComments } from '../components/ShareBar';
import { RelatedNews, RelatedProducts } from '../components/RelatedWidgets';
import AdSlot from '../ads/AdSlot';
import InArticleBody from '../ads/InArticleBody';
import { useAdConfig } from '../ads/adsConfig';
import { timeAgo } from '../api';

function Toc({ html }) {
  const [heads, setHeads] = useState([]);
  useEffect(() => {
    const div = document.createElement('div');
    div.innerHTML = html || '';
    setHeads([...div.querySelectorAll('h2')].slice(0, 5).map(h => h.textContent));
  }, [html]);
  if (!heads.length) return null;
  return (
    <Box sx={{ p: 2, bgcolor: '#f1f5f9', borderRadius: 2, mb: 2 }}>
      <Typography variant="subtitle2" fontWeight={800}>In this story</Typography>
      {heads.map((h, i) => <Typography key={i} variant="body2">• {h}</Typography>)}
    </Box>
  );
}

export default function NobleSeekDetailPage() {
  const { slug } = useParams();
  const [searchParams] = useSearchParams();
  const isAmp = searchParams.get('amp') === '1';
  const [article, setArticle] = useState(null);
  const [loading, setLoading] = useState(true);
  const adConfig = useAdConfig();

  useEffect(() => {
    setLoading(true);
    fetchNewsDetail(slug).then(setArticle).catch(() => setArticle(null)).finally(() => setLoading(false));
    window.scrollTo(0, 0);
  }, [slug]);

  if (loading) {
    return (
      <Container maxWidth="md" sx={{ py: 3 }}>
        <Skeleton variant="rectangular" height={300} sx={{ borderRadius: 3 }} />
        <Skeleton width="80%" height={40} sx={{ mt: 2 }} />
        <Skeleton width="100%" height={120} /><Skeleton width="100%" height={200} />
      </Container>
    );
  }
  if (!article) {
    return (
      <Container maxWidth="md" sx={{ py: 6, textAlign: 'center' }}>
        <Typography variant="h5" fontWeight={800}>Story not found</Typography>
        <Button component={Link} to="/nobleseek" variant="contained" sx={{ mt: 2 }}>Back to NobleSeek</Button>
      </Container>
    );
  }

  const slots = { inarticle1: adConfig.slot_inarticle_1, inarticle2: adConfig.slot_inarticle_2, multiplex: adConfig.slot_multiplex };

  // AMP-lite: ultra-fast minimal markup for FB mobile clicks (?amp=1).
  if (isAmp) {
    return (
      <Container maxWidth="sm" sx={{ py: 2, bgcolor: 'white' }}>
        <NewsSeo title={article.seo_title || article.headline} description={article.seo_description || article.excerpt} image={article.hero_image} slug={article.slug} jsonLd={article.json_ld} />
        <Typography variant="h5" fontWeight={900}>{article.headline_bn || article.headline}</Typography>
        {article.hero_image && <Box component="img" src={article.hero_image} alt={article.hero_image_alt || article.headline} loading="eager" sx={{ width: '100%', borderRadius: 2, my: 1.5 }} />}
        <AdSlot slot={adConfig.slot_top} format="auto" minHeight={100} />
        <div dangerouslySetInnerHTML={{ __html: article.body_html }} />
        <AdSlot slot={adConfig.slot_inarticle_1} format="auto" minHeight={100} />
        <Button component={Link} to={`/nobleseek/${article.slug}`} variant="outlined" fullWidth sx={{ mt: 2 }}>View full experience</Button>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 3 }}>
      <NewsSeo title={article.seo_title || article.headline} description={article.seo_description || article.excerpt} image={article.hero_image} slug={article.slug} jsonLd={article.json_ld} />
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        <Link to="/nobleseek" style={{ textDecoration: 'none' }}>NobleSeek</Link>
        {article.category_name ? ` / ${article.category_name}` : ''} / {article.slug}
        {' • '}<Link to={`/nobleseek/${article.slug}?amp=1`} style={{ textDecoration: 'underline' }}>Fast ⚡ AMP</Link>
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Typography variant="h4" fontWeight={900} sx={{ lineHeight: 1.25, mb: 1 }}>
            {article.headline_bn || article.headline}
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap', mb: 1.5 }}>
            <Chip size="small" label={article.category_name || 'News'} color="secondary" />
            {article.is_breaking && <Chip size="small" label="BREAKING" color="error" />}
            <Typography variant="caption" color="text.secondary">{timeAgo(article.published_at)} • {article.read_time_minutes} min read • {article.view_count} views</Typography>
            {article.source_name && <Typography variant="caption" color="text.secondary">Source: {article.source_url ? <a href={article.source_url} target="_blank" rel="noreferrer">{article.source_name}</a> : article.source_name}</Typography>}
          </Box>

          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
            <Typography variant="caption" color="text.secondary">By NobleSeek Desk • Dhaka</Typography>
            <ShareBar title={article.headline} />
          </Box>

          {/* MAX ADS block 1: top leaderboard */}
          <AdSlot slot={adConfig.slot_top} format="auto" minHeight={110} />

          {article.hero_image && (
            <Box sx={{ mb: 1 }}>
              <Box component="img" src={article.hero_image} alt={article.hero_image_alt || article.headline} loading="eager" fetchPriority="high" sx={{ width: '100%', borderRadius: 3, maxHeight: 480, objectFit: 'cover' }} />
              {article.image_credit && <Typography variant="caption" color="text.secondary">Photo: {article.image_credit}</Typography>}
            </Box>
          )}
          {article.excerpt && <Typography variant="subtitle1" sx={{ p: 1.5, bgcolor: '#fffbeb', borderLeft: '4px solid #f59e0b', borderRadius: 1, mb: 2 }}>{article.excerpt}</Typography>}

          <Toc html={article.body_html} />
          <Box sx={{ '& img': { maxWidth: '100%', borderRadius: 2 }, '& h2': { mt: 3, fontSize: '1.25rem' }, '& p': { lineHeight: 1.85, mb: 1.5 }, fontSize: '1.02rem' }}>
            <InArticleBody html={article.body_html} slots={slots} />
          </Box>

          {article.tags?.length > 0 && (
            <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap', mt: 2 }}>
              {article.tags.map((t) => <Chip key={t} size="small" label={`#${t}`} variant="outlined" />)}
            </Box>
          )}
          <Divider sx={{ my: 2 }} />
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="body2" fontWeight={700}>Share this story</Typography>
            <ShareBar title={article.headline} />
          </Box>
          <RelatedProducts productIds={article.related_product_ids} />
          <FacebookComments />
          <RelatedNews slug={article.slug} />
        </Grid>

        <Grid item xs={12} md={4}>
          <Box sx={{ position: { md: 'sticky' }, top: 76, display: 'flex', flexDirection: 'column', gap: 0 }}>
            {/* Sidebar sticky 300x600 = highest viewability */}
            <AdSlot slot={adConfig.slot_sidebar} format="auto" minHeight={600} style={{ margin: '0 0 20px' }} />
            <Box sx={{ p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 3, bgcolor: 'white' }}>
              <Typography variant="subtitle1" fontWeight={800}>Follow NobleSeek</Typography>
              <Typography variant="body2" color="text.secondary">প্রতিদিনের ট্রেন্ড খবর সবার আগে পেতে ফেসবুক পেজ ফলো করুন।</Typography>
              <Button component="a" href="https://www.facebook.com/" target="_blank" rel="noreferrer" variant="contained" fullWidth sx={{ mt: 1.5 }}>Follow on Facebook</Button>
              <Button component={Link} to="/shop" variant="outlined" fullWidth sx={{ mt: 1 }}>Shop on Fabrything</Button>
            </Box>
            <AdSlot slot={adConfig.slot_multiplex} format="autorelaxed" minHeight={250} />
          </Box>
        </Grid>
      </Grid>
    </Container>
  );
}
