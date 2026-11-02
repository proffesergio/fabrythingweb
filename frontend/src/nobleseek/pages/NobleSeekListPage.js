import React, { useCallback, useEffect, useState } from 'react';
import { Box, Container, Grid, Typography, Button, Skeleton } from '@mui/material';
import { useSearchParams, Link } from 'react-router-dom';
import { fetchNewsList, fetchNewsCategories, fetchSection, sectionName } from '../api';
import { LeadCard, SecondaryCard, HorizontalCard, SectionHeader } from '../components/NewsCards';
import MostRead, { OpinionBox } from '../components/MostRead';
import PollWidget from '../components/PollWidget';
import NewsSeo from '../components/NewsSeo';
import AdSlot from '../ads/AdSlot';
import { useAdConfig } from '../ads/adsConfig';

const HOME_SECTIONS = ['sports', 'entertainment', 'tech', 'world', 'economy'];

function PortalHome() {
  const [cats, setCats] = useState([]);
  const [latest, setLatest] = useState([]);
  const [count, setCount] = useState(0);
  const [sections, setSections] = useState({});
  const [loading, setLoading] = useState(true);
  const adConfig = useAdConfig();

  useEffect(() => {
    let live = true;
    async function load() {
      try {
        const [c, l] = await Promise.all([
          fetchNewsCategories().catch(() => []),
          fetchNewsList({}).catch(() => ({ results: [], count: 0 })),
        ]);
        if (!live) return;
        setCats(c || []);
        setLatest(l.results || []);
        setCount(l.count || 0);
        setLoading(false);
        const entries = await Promise.all(
          HOME_SECTIONS.map((s) => fetchSection(s, 4).then((r) => [s, r]).catch(() => [s, []]))
        );
        if (live) setSections(Object.fromEntries(entries));
      } catch { if (live) setLoading(false); }
    }
    load();
    return () => { live = false; };
  }, []);

  const hero = latest.find((a) => a.is_breaking) || latest.find((a) => a.is_featured) || latest[0];
  const secondary = latest.filter((a) => a !== hero).slice(0, 2);
  const grid = latest.filter((a) => a !== hero && !secondary.includes(a)).slice(0, 6);

  return (
    <Container maxWidth="lg" sx={{ py: { xs: 2, md: 3 } }}>
      <NewsSeo title="সর্বশেষ সংবাদ" description="নোবেলসিক — দেশ-বিদেশের সর্বশেষ সংবাদ, বিশ্লেষণ ও মতামত।" slug="" />
      {loading ? (
        <Grid container spacing={2}>
          <Grid item xs={12} md={8}><Skeleton variant="rectangular" height={380} sx={{ borderRadius: 3 }} /></Grid>
          <Grid item xs={12} md={4}><Skeleton variant="rectangular" height={380} sx={{ borderRadius: 2 }} /></Grid>
        </Grid>
      ) : (
        <>
          {/* Lead row: hero + 2 secondary + opinion column */}
          <Grid container spacing={2.5}>
            <Grid item xs={12} md={6}>
              {hero && <LeadCard article={hero} utm="portal-lead" />}
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {secondary.map((a) => <SecondaryCard key={a.id || a.slug} article={a} utm="portal-secondary" />)}
              </Box>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <OpinionBox />
            </Grid>
          </Grid>

          <AdSlot slot={adConfig.slot_shop_subtle} format="auto" minHeight={90} />

          {/* Latest + most-read */}
          <Grid container spacing={3}>
            <Grid item xs={12} md={8}>
              <SectionHeader title={`সর্বশেষ (${count}টি খবর)`} to="/nobleseek?search=" actionLabel="সব খবর" />
              <Grid container spacing={2.5}>
                {grid.map((a) => (
                  <Grid item xs={12} sm={6} key={a.id || a.slug}>
                    <SecondaryCard article={a} utm="portal-latest" />
                  </Grid>
                ))}
              </Grid>
              {!latest.length && (
                <Box sx={{ textAlign: 'center', py: 6 }}>
                  <Typography variant="h6" className="ns-serif">এখনো কোনো খবর প্রকাশ হয়নি</Typography>
                  <Typography variant="body2" color="text.secondary" className="ns-sans">ডেস্ক থেকে প্রথম প্রতিবেদন প্রকাশের অপেক্ষায়।</Typography>
                </Box>
              )}
              {grid.length > 0 && (
                <Box sx={{ textAlign: 'center', mt: 2 }}>
                  <Button component={Link} to="/nobleseek?search=" variant="outlined" sx={{ borderColor: '#ddd', color: '#141414' }} className="ns-sans">আরও খবর পড়ুন</Button>
                </Box>
              )}
            </Grid>
            <Grid item xs={12} md={4}>
              <Box sx={{ position: { md: 'sticky' }, top: 70, display: 'flex', flexDirection: 'column', gap: 2 }}>
                <MostRead latest={latest} />
                <PollWidget />
                <AdSlot slot={adConfig.slot_sidebar} format="auto" minHeight={250} />
              </Box>
            </Grid>
          </Grid>

          {/* Category sections */}
          {HOME_SECTIONS.map((s) => {
            const items = sections[s] || [];
            if (!items.length) return null;
            return (
              <Box key={s}>
                <SectionHeader title={sectionName(s, cats)} to={`/nobleseek?category=${s}`} />
                <Grid container spacing={2.5}>
                  {items.slice(0, 4).map((a) => (
                    <Grid item xs={12} sm={6} md={3} key={a.id || a.slug}>
                      <SecondaryCard article={a} utm={`portal-${s}`} />
                    </Grid>
                  ))}
                </Grid>
              </Box>
            );
          })}
          <AdSlot slot={adConfig.slot_multiplex} format="autorelaxed" minHeight={200} />
        </>
      )}
    </Container>
  );
}

// Section / search listing with Load More pagination.
function ListingView({ category, search, cats }) {
  const [items, setItems] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const adConfig = useAdConfig();

  const loadPage = useCallback(async (p, append) => {
    if (append) setLoadingMore(true); else setLoading(true);
    try {
      const res = await fetchNewsList({ category, search, page: p });
      setItems((prev) => (append ? [...prev, ...res.results] : res.results));
      setCount(res.count);
    } finally { setLoading(false); setLoadingMore(false); }
  }, [category, search]);

  useEffect(() => {
    setPage(1);
    setItems([]);
    loadPage(1, false);
  }, [category, search, loadPage]);

  const title = search ? `অনুসন্ধান: “${search}”` : sectionName(category, cats);
  const hasMore = items.length < count;

  return (
    <Container maxWidth="lg" sx={{ py: { xs: 2, md: 3 } }}>
      <NewsSeo title={title} description={`${title} — নোবেলসিকের সব খবর এক জায়গায়।`} slug="" />
      <Box sx={{ borderBottom: '2px solid #141414', pb: 1, mb: 2.5 }}>
        <Typography variant="h4" fontWeight={900} className="ns-serif" sx={{ fontSize: { xs: '1.5rem', md: '2rem' } }}>{title}</Typography>
        <Typography variant="body2" color="text.secondary" className="ns-sans">{count}টি খবর পাওয়া গেছে</Typography>
      </Box>
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          {loading ? (
            <Grid container spacing={2.5}>
              {[1, 2, 3, 4].map((i) => (
                <Grid item xs={12} sm={6} key={i}>
                  <Skeleton variant="rectangular" height={180} sx={{ borderRadius: 2 }} />
                  <Skeleton width="90%" sx={{ mt: 1 }} />
                </Grid>
              ))}
            </Grid>
          ) : (
            <>
              <Grid container spacing={2.5}>
                {items.map((a, i) => (
                  <React.Fragment key={a.id || a.slug}>
                    <Grid item xs={12} sm={6}>
                      <SecondaryCard article={a} />
                    </Grid>
                    {(i === 1 || i === 5) && (
                      <Grid item xs={12}>
                        <AdSlot slot={i === 1 ? adConfig.slot_inarticle_1 : adConfig.slot_multiplex} format="auto" minHeight={100} />
                      </Grid>
                    )}
                  </React.Fragment>
                ))}
              </Grid>
              {!items.length && (
                <Box sx={{ textAlign: 'center', py: 6 }}>
                  <Typography variant="h6" className="ns-serif">কোনো খবর পাওয়া যায়নি</Typography>
                  <Button component={Link} to="/nobleseek" variant="outlined" sx={{ mt: 2 }} className="ns-sans">প্রচ্ছদে ফিরুন</Button>
                </Box>
              )}
              {hasMore && (
                <Box sx={{ textAlign: 'center', mt: 3 }}>
                  <Button variant="contained" disabled={loadingMore} onClick={() => { const n = page + 1; setPage(n); loadPage(n, true); }} sx={{ bgcolor: '#141414' }} className="ns-sans">
                    {loadingMore ? 'লোড হচ্ছে…' : 'আরও খবর লোড করুন'}
                  </Button>
                </Box>
              )}
            </>
          )}
        </Grid>
        <Grid item xs={12} md={4}>
          <Box sx={{ position: { md: 'sticky' }, top: 70, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <MostRead latest={items} />
            <AdSlot slot={adConfig.slot_sidebar} format="auto" minHeight={250} />
          </Box>
        </Grid>
      </Grid>
    </Container>
  );
}

export default function NobleSeekListPage() {
  const [params] = useSearchParams();
  const category = params.get('category') || '';
  const search = params.get('search') || '';
  const [cats, setCats] = useState([]);

  useEffect(() => {
    fetchNewsCategories().then((c) => { if (Array.isArray(c)) setCats(c); }).catch(() => {});
  }, []);

  // Portal front page when no filter; listing view for section/search.
  // `?search=` (empty) from "সব খবর" buttons shows the full archive.
  if (!category && !search && !params.has('search')) return <PortalHome />;
  return <ListingView category={category} search={search} cats={cats} />;
}
