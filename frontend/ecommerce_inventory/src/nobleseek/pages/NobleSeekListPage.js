import React, { useEffect, useState, useCallback } from 'react';
import { Box, Container, Grid, Typography, Chip, TextField, Button, Skeleton } from '@mui/material';
import { useSearchParams, Link } from 'react-router-dom';
import { fetchNewsList, fetchNewsCategories } from '../api';
import NewsCard, { NewsCardSkeleton } from '../components/NewsCard';
import NewsSeo from '../components/NewsSeo';
import AdSlot from '../ads/AdSlot';
import { useAdConfig } from '../ads/adsConfig';

export default function NobleSeekListPage() {
  const [params, setParams] = useSearchParams();
  const category = params.get('category') || '';
  const [cats, setCats] = useState([]);
  const [items, setItems] = useState([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState(params.get('search') || '');
  const adConfig = useAdConfig();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [c, l] = await Promise.all([
        fetchNewsCategories().catch(() => []),
        fetchNewsList({ category, search: params.get('search') || '' }),
      ]);
      setCats(c || []);
      setItems(l.results || []);
      setCount(l.count || 0);
    } finally { setLoading(false); }
  }, [category, params]);

  useEffect(() => { load(); }, [load]);

  const hero = items[0];
  const rest = items.slice(1);

  return (
    <Container maxWidth="lg" sx={{ py: 3 }}>
      <NewsSeo title="Latest Trends News" description="NobleSeek — Google Trends based daily Bangla news. Headlines, details, photos." slug="" />
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1 }}>
        <Typography variant="h4" fontWeight={900}>NobleSeek</Typography>
        <Chip label={`${count} stories`} size="small" color="secondary" />
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Google Trends কীওয়ার্ড থেকে প্রতিদিনের বাছাই খবর — ফেসবুক NobleSeek পেজ থেকে সরাসরি।
      </Typography>

      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
        <Chip label="All" clickable color={!category ? 'secondary' : 'default'} onClick={() => setParams({})} />
        {cats.map((c) => (
          <Chip key={c.slug} label={c.name} clickable color={category === c.slug ? 'secondary' : 'default'} onClick={() => setParams({ category: c.slug })} />
        ))}
        <Box sx={{ flex: 1 }} />
        <TextField size="small" placeholder="Search news…" value={search} onChange={(e) => setSearch(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') setParams(search ? { search } : {}); }} />
      </Box>

      {loading ? (
        <Grid container spacing={2}>
          {[1, 2, 3, 4, 5, 6].map((i) => <Grid item xs={12} sm={6} md={4} key={i}><NewsCardSkeleton /></Grid>)}
        </Grid>
      ) : (
        <>
          {hero && (
            <Box component={Link} to={`/nobleseek/${hero.slug}?utm_source=facebook&utm_medium=social&utm_campaign=nobleseek-fb`} sx={{ textDecoration: 'none', color: 'inherit', display: 'block', mb: 3, borderRadius: 3, overflow: 'hidden', position: 'relative', minHeight: 280, bgcolor: '#0f172a' }}>
              {hero.hero_image && <Box component="img" src={hero.hero_image} alt={hero.headline} loading="eager" fetchPriority="high" sx={{ width: '100%', height: { xs: 240, md: 380 }, objectFit: 'cover' }} />}
              <Box sx={{ position: 'absolute', bottom: 0, left: 0, right: 0, p: 2.5, background: 'linear-gradient(transparent, rgba(0,0,0,0.85))', color: 'white' }}>
                <Chip size="small" label={hero.category_name || 'Top story'} color="secondary" sx={{ mb: 1 }} />
                <Typography variant="h5" fontWeight={900} sx={{ lineHeight: 1.25 }}>{hero.headline_bn || hero.headline}</Typography>
                <Typography variant="caption">{hero.read_time_minutes} min read • {hero.view_count} views</Typography>
              </Box>
            </Box>
          )}
          <AdSlot slot={adConfig.slot_shop_subtle} format="auto" minHeight={90} />
          <Grid container spacing={2}>
            {rest.map((a) => (
              <Grid item xs={12} sm={6} md={4} key={a.id || a.slug}>
                <NewsCard article={a} />
              </Grid>
            ))}
          </Grid>
          {!items.length && (
            <Box sx={{ textAlign: 'center', py: 6 }}>
              <Typography variant="h6">No stories yet</Typography>
              <Typography variant="body2" color="text.secondary">Publish from Admin → NobleSeek → Trends Inbox.</Typography>
              <Button component={Link} to="/shop" variant="contained" sx={{ mt: 2 }}>Back to Shop</Button>
            </Box>
          )}
          {items.length > 2 && <AdSlot slot={adConfig.slot_multiplex} format="autorelaxed" minHeight={200} />}
        </>
      )}
      <Box sx={{ display: 'none' }}><Skeleton /></Box>
    </Container>
  );
}
