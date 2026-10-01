import React, { useEffect, useState } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import { Box, Container, Typography, Chip, Grid, Skeleton, Divider, Button, LinearProgress } from '@mui/material';
import { fetchNewsDetail, sectionName, fetchNewsCategories } from '../api';
import { formatNewsTime, formatViews, timeAgoBn } from '../bn';
import NewsSeo from '../components/NewsSeo';
import ShareBar, { FacebookComments } from '../components/ShareBar';
import { RelatedNews } from '../components/RelatedWidgets';
import MostRead from '../components/MostRead';
import AdSlot from '../ads/AdSlot';
import InArticleBody from '../ads/InArticleBody';
import { useAdConfig } from '../ads/adsConfig';
import { NS_ACCENT, NS_NAVY } from '../portal/PortalHeader';

function ReadingProgress() {
  const [pct, setPct] = useState(0);
  useEffect(() => {
    const onScroll = () => {
      const h = document.documentElement;
      const max = h.scrollHeight - h.clientHeight;
      setPct(max > 0 ? Math.min(100, (h.scrollTop / max) * 100) : 0);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);
  return <LinearProgress variant="determinate" value={pct} sx={{ position: 'fixed', top: 0, left: 0, right: 0, zIndex: 1300, height: 3, bgcolor: 'transparent', '& .MuiLinearProgress-bar': { bgcolor: NS_ACCENT } }} />;
}

export default function NobleSeekDetailPage() {
  const { slug } = useParams();
  const [searchParams] = useSearchParams();
  const isAmp = searchParams.get('amp') === '1';
  const [article, setArticle] = useState(null);
  const [cats, setCats] = useState([]);
  const [loading, setLoading] = useState(true);
  const adConfig = useAdConfig();

  useEffect(() => {
    setLoading(true);
    fetchNewsCategories().then((c) => { if (Array.isArray(c)) setCats(c); }).catch(() => {});
    fetchNewsDetail(slug).then(setArticle).catch(() => setArticle(null)).finally(() => setLoading(false));
    window.scrollTo(0, 0);
  }, [slug]);

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Skeleton variant="rectangular" height={340} sx={{ borderRadius: 2 }} />
        <Skeleton width="70%" height={44} sx={{ mt: 2 }} />
        <Skeleton width="100%" height={120} /><Skeleton width="100%" height={220} />
      </Container>
    );
  }
  if (!article) {
    return (
      <Container maxWidth="md" sx={{ py: 8, textAlign: 'center' }}>
        <Typography variant="h5" fontWeight={800} className="ns-serif">দুঃখিত, খবরটি পাওয়া যায়নি</Typography>
        <Typography variant="body2" color="text.secondary" className="ns-sans" sx={{ mt: 1 }}>লিংকটি ভুল হতে পারে অথবা খবরটি সরিয়ে নেওয়া হয়েছে।</Typography>
        <Button component={Link} to="/nobleseek" variant="contained" sx={{ mt: 2, bgcolor: '#141414' }} className="ns-sans">প্রচ্ছদে ফিরুন</Button>
      </Container>
    );
  }

  const slots = { inarticle1: adConfig.slot_inarticle_1, inarticle2: adConfig.slot_inarticle_2, multiplex: adConfig.slot_multiplex };
  const catLabel = article.category_slug ? sectionName(article.category_slug, cats) : (article.category_name || 'সংবাদ');

  // AMP-lite: ultra-fast minimal markup (?amp=1).
  if (isAmp) {
    return (
      <Container maxWidth="sm" sx={{ py: 2, bgcolor: 'white' }}>
        <NewsSeo title={article.seo_title || article.headline} description={article.seo_description || article.excerpt} image={article.hero_image} slug={article.slug} jsonLd={article.json_ld} />
        <Typography variant="h5" fontWeight={900} className="ns-serif">{article.headline_bn || article.headline}</Typography>
        {article.hero_image && <Box component="img" src={article.hero_image} alt={article.hero_image_alt || article.headline} loading="eager" sx={{ width: '100%', borderRadius: 2, my: 1.5 }} />}
        <AdSlot slot={adConfig.slot_top} format="auto" minHeight={100} />
        <div dangerouslySetInnerHTML={{ __html: article.body_html }} />
        <AdSlot slot={adConfig.slot_inarticle_1} format="auto" minHeight={100} />
        <Button component={Link} to={`/nobleseek/${article.slug}`} variant="outlined" fullWidth sx={{ mt: 2 }} className="ns-sans">পূর্ণ সংস্করণ পড়ুন</Button>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: { xs: 2, md: 3 } }}>
      <ReadingProgress />
      <NewsSeo title={article.seo_title || article.headline} description={article.seo_description || article.excerpt} image={article.hero_image} slug={article.slug} jsonLd={article.json_ld} />

      {/* Breadcrumb */}
      <Typography variant="body2" className="ns-sans" sx={{ mb: 1.5, color: '#666' }}>
        <Link to="/nobleseek" style={{ textDecoration: 'none', color: 'inherit' }}>প্রচ্ছদ</Link>
        {' / '}
        {article.category_slug
          ? <Link to={`/nobleseek?category=${article.category_slug}`} style={{ textDecoration: 'none', color: 'inherit' }}>{catLabel}</Link>
          : catLabel}
        {' • '}<Link to={`/nobleseek/${article.slug}?amp=1`} style={{ color: NS_ACCENT }}>দ্রুত সংস্করণ ⚡</Link>
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
            <Chip size="small" label={catLabel} sx={{ bgcolor: NS_ACCENT, color: 'white', fontWeight: 700 }} className="ns-sans" />
            {article.is_breaking && <Chip size="small" label="ব্রেকিং" color="error" className="ns-sans" />}
          </Box>

          <Typography variant="h3" fontWeight={900} className="ns-serif" sx={{ lineHeight: 1.4, fontSize: { xs: '1.55rem', md: '2.1rem' }, mb: 1.5 }}>
            {article.headline_bn || article.headline}
          </Typography>

          {article.excerpt && (
            <Typography variant="subtitle1" className="ns-sans" sx={{ color: '#444', lineHeight: 1.8, borderLeft: `3px solid ${NS_ACCENT}`, pl: 1.5, mb: 2 }}>
              {article.excerpt}
            </Typography>
          )}

          {/* Byline row */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap', py: 1.2, borderTop: '1px solid #eee', borderBottom: '1px solid #eee', mb: 2 }}>
            <Box>
              <Typography variant="body2" fontWeight={800} className="ns-sans">নোবেলসিক ডেস্ক, ঢাকা</Typography>
              <Typography variant="caption" color="text.secondary" className="ns-sans">
                প্রকাশ: {formatNewsTime(article.published_at)}
                {article.updated_at && article.updated_at !== article.published_at ? ` • আপডেট: ${timeAgoBn(article.updated_at)}` : ''}
                {` • ${formatViews(article.view_count)} পঠিত • ${article.read_time_minutes} মিনিটে পড়ুন`}
              </Typography>
            </Box>
            <Box sx={{ flex: 1 }} />
            <ShareBar title={article.headline_bn || article.headline} />
          </Box>

          {article.source_name && (
            <Typography variant="caption" color="text.secondary" className="ns-sans" sx={{ display: 'block', mb: 1 }}>
              তথ্যসূত্র: {article.source_url ? <a href={article.source_url} target="_blank" rel="noreferrer">{article.source_name}</a> : article.source_name}
            </Typography>
          )}

          <AdSlot slot={adConfig.slot_top} format="auto" minHeight={110} />

          {article.hero_image && (
            <Box sx={{ mb: 2 }}>
              <Box component="img" src={article.hero_image} alt={article.hero_image_alt || article.headline} loading="eager" fetchPriority="high" sx={{ width: '100%', borderRadius: 2, maxHeight: 520, objectFit: 'cover' }} />
              {article.image_credit && <Typography variant="caption" color="text.secondary" className="ns-sans">ছবি: {article.image_credit}</Typography>}
            </Box>
          )}

          <Box className="ns-sans" sx={{ '& img': { maxWidth: '100%', borderRadius: 2 }, '& h2': { mt: 3, fontSize: '1.3rem', fontFamily: "'Noto Serif Bengali', serif", fontWeight: 800 }, '& p': { lineHeight: 1.95, mb: 1.75, fontSize: '1.05rem', color: '#222' }, '& ul': { lineHeight: 1.9 } }}>
            <InArticleBody html={article.body_html} slots={slots} dropCap />
          </Box>

          {article.tags?.length > 0 && (
            <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap', mt: 3 }}>
              <Typography variant="body2" fontWeight={800} className="ns-sans">বিষয়:</Typography>
              {article.tags.map((t) => <Chip key={t} size="small" label={`#${t}`} variant="outlined" className="ns-sans" />)}
            </Box>
          )}

          <Divider sx={{ my: 2.5 }} />
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
            <Typography variant="body2" fontWeight={800} className="ns-sans">খবরটি শেয়ার করুন</Typography>
            <ShareBar title={article.headline_bn || article.headline} />
          </Box>

          <FacebookComments />
          <RelatedNews slug={article.slug} />
        </Grid>

        <Grid item xs={12} md={4}>
          <Box sx={{ position: { md: 'sticky' }, top: 70, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <AdSlot slot={adConfig.slot_sidebar} format="auto" minHeight={300} />
            <MostRead />
            <Box sx={{ p: 2.5, borderRadius: 2, bgcolor: NS_NAVY, color: 'white', textAlign: 'center' }}>
              <Typography variant="subtitle1" fontWeight={900} className="ns-serif">নোবেলসিক ফলো করুন</Typography>
              <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)', mt: 0.5 }} className="ns-sans">সর্বশেষ খবর সবার আগে পেতে ফেসবুক পেজে যুক্ত হোন।</Typography>
              <Button component="a" href="https://www.facebook.com/" target="_blank" rel="noreferrer" variant="contained" fullWidth sx={{ mt: 1.5, bgcolor: NS_ACCENT }} className="ns-sans">ফেসবুকে ফলো করুন</Button>
            </Box>
            <AdSlot slot={adConfig.slot_multiplex} format="autorelaxed" minHeight={250} />
          </Box>
        </Grid>
      </Grid>
    </Container>
  );
}
