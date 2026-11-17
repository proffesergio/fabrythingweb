import React, { useCallback, useEffect, useLayoutEffect, useState } from 'react';
import { completeStoreDocument } from '../../utils/storeDocument';
import { Box, Container, Grid, Typography, Button, Skeleton } from '@mui/material';
import { useSearchParams, Link } from 'react-router-dom';
import { fetchNewsList, fetchNewsCategories, fetchSection, sectionName, articleUrl } from '../api';
import { timeAgoBn } from '../bn';
import { LeadCard, SecondaryCard, SectionHeader } from '../components/NewsCards';
import MostRead, { FacebookFollow } from '../components/MostRead';
import PollWidget from '../components/PollWidget';
import NewsSeo from '../components/NewsSeo';
import AdSlot from '../ads/AdSlot';
import { useAdConfig } from '../ads/adsConfig';

const HOME_SECTIONS = ['sports', 'tech', 'bangladesh', 'world', 'economy', 'politics', 'entertainment', 'lifestyle', 'opinion'];

function PortalHome() {
  const [cats, setCats] = useState([]);
  const [latest, setLatest] = useState([]);
  const [count, setCount] = useState(0);
  const [sections, setSections] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);
  const adConfig = useAdConfig();
  useLayoutEffect(() => { if (!loading && !error) completeStoreDocument(); }, [loading, error]);

  useEffect(() => {
    let live = true;
    async function load() {
      setLoading(true);
      setError(false);
      try {
        const [c, l] = await Promise.all([
          fetchNewsCategories().catch(() => []),
          fetchNewsList({ pageSize: 24 }),
        ]);
        if (!live) return;
        setCats(c || []);
        setLatest(l.results || []);
        setCount(l.count || 0);
        setLoading(false);
        // Bound concurrent requests so the richer newspaper does not swamp a
        // waking API. Each populated section becomes usable as it arrives.
        for (let index = 0; index < HOME_SECTIONS.length && live; index += 3) {
          const entries = await Promise.all(HOME_SECTIONS.slice(index, index + 3)
            .map((s) => fetchSection(s, 5).then((r) => [s, r]).catch(() => [s, []])));
          if (live) setSections((previous) => ({ ...previous, ...Object.fromEntries(entries) }));
        }
      } catch { if (live) { setError(true); setLoading(false); } }
    }
    load();
    return () => { live = false; };
  }, [retry]);

  const hero = latest.find((a) => a.is_breaking) || latest.find((a) => a.is_featured) || latest[0];
  const secondary = latest.filter((a) => a !== hero).slice(0, 2);
  const rail = latest.filter((a) => a !== hero && !secondary.includes(a)).slice(0, 5);
  const grid = latest.filter((a) => a !== hero && !secondary.includes(a) && !rail.includes(a)).slice(0, 12);

  const visibleSections = HOME_SECTIONS.filter((section) => section !== 'opinion' && sections[section]?.length);
  return (
    <Container maxWidth={false} sx={{ maxWidth: 1280, py: { xs: 2.5, md: 4 }, bgcolor: '#FEFEFE', color: '#040D33', overflowWrap: 'anywhere' }}>
      <NewsSeo title="সর্বশেষ সংবাদ" description="নোবেলসিক — দেশ-বিদেশের সর্বশেষ সংবাদ, বিশ্লেষণ ও মতামত।" slug="" />
      {loading ? <Box role="status" aria-label="সংবাদ লোড হচ্ছে"><Skeleton variant="rectangular" height={380} /></Box> : error ? (
        <Box role="alert" sx={{ py: 6 }}>
          <Typography component="h1" variant="h5" className="ns-serif">খবর লোড করা যায়নি</Typography>
          <Button onClick={() => setRetry((value) => value + 1)} sx={{ mt: 2 }}>আবার চেষ্টা করুন</Button>
        </Box>
      ) : (
        <>
          <Box data-news-lead sx={{ display: 'grid', gridTemplateColumns: { xs: 'minmax(0, 1fr)', md: 'minmax(0, 5fr) minmax(0, 3fr) minmax(0, 4fr)' }, gap: { xs: 3, lg: 4 }, alignItems: 'start' }}>
            <Box sx={{ minWidth: 0, pr: { md: 3 }, borderRight: { md: '1px solid #E8E8E8' } }}>
              {hero ? <LeadCard article={hero} utm="portal-lead" /> : <Box sx={{ py: 6 }}><Typography component="h1" variant="h5" className="ns-serif">এখনো কোনো খবর প্রকাশ হয়নি</Typography><Typography className="ns-sans" sx={{ mt: 1 }}>ডেস্ক থেকে প্রথম প্রতিবেদন প্রকাশের অপেক্ষায়।</Typography></Box>}
            </Box>
            <Box sx={{ minWidth: 0, display: 'flex', flexDirection: 'column', gap: 3, pr: { md: 3 }, borderRight: { md: '1px solid #E8E8E8' }, '& > :not(:last-child)': { pb: 3, borderBottom: '1px solid #E8E8E8' } }}>
              {secondary.map((article) => <SecondaryCard key={article.id || article.slug} article={article} heading="h2" utm="portal-secondary" />)}
            </Box>
            <Box component="aside" aria-label="সংবাদ ও পাঠক" sx={{ minWidth: 0, display: 'flex', flexDirection: 'column', gap: 3 }}>
              <MostRead latest={rail} />
              {adConfig.slot_sidebar && <AdSlot placement="sidebar" slot={adConfig.slot_sidebar} format="auto" minHeight={250} />}
            </Box>
          </Box>
          {adConfig.slot_shop_subtle && <Box sx={{ maxWidth: 970, mx: 'auto', my: 4 }}><AdSlot placement="leaderboard" slot={adConfig.slot_shop_subtle} format="auto" minHeight={90} /></Box>}
          {grid.length > 0 && <Box component="section" aria-label="সর্বশেষ সংবাদ" sx={{ mt: 4 }}>
            <SectionHeader title={`সর্বশেষ (${count}টি খবর)`} to="/nobleseek?search=" actionLabel="সব খবর" />
            <NewsRow items={grid} utm="portal-latest" />
          </Box>}
          {!grid.length && <SectionHeader title={`সর্বশেষ (${count}টি খবর)`} to="/nobleseek?search=" actionLabel="সব খবর" />}
          {count > 12 && <Button component={Link} to="/nobleseek?page=2" sx={{ mt: 2 }}>পরের পৃষ্ঠা</Button>}
          <Box data-news-topics sx={{ display: 'grid', gridTemplateColumns: { xs: 'minmax(0, 1fr)', md: 'repeat(2, minmax(0, 1fr))' }, columnGap: { xs: 3, md: 6 }, rowGap: 1, mt: 2 }}>
            {visibleSections.map((section) => <TopicSection key={section} title={sectionName(section, cats)} section={section} articles={sections[section]} />)}
          </Box>
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'minmax(0,1fr)', md: 'minmax(0,2fr) minmax(0,1fr)' }, gap: 4, mt: 5, pt: 4, borderTop: '1px solid #E8E8E8' }}>
            <Box>
              {sections.opinion?.length > 0 && <>
                <SectionHeader title="মতামত ও বিশ্লেষণ" to="/nobleseek?category=opinion" sx={{ mt: 0 }} />
                <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'minmax(0,1fr)', sm: 'repeat(2,minmax(0,1fr))' }, gap: 3 }}>
                  {sections.opinion.slice(0, 2).map((article, index) => <Box key={article.id || article.slug} component={Link} to={articleUrl(article.slug)} sx={{ p: 3, bgcolor: index ? '#F5F8FA' : '#FDF6E3', border: '1px solid #E8E8E8', textDecoration: 'none', color: 'inherit' }}>
                    <Typography component="h3" className="ns-serif" sx={{ fontSize: 19, fontWeight: 800, lineHeight: 1.5 }}>{article.headline_bn || article.headline}</Typography>
                    <Typography className="ns-sans ns-clamp-3" sx={{ mt: 1, color: '#555', fontSize: 15 }}>{article.excerpt}</Typography>
                  </Box>)}
                </Box>
              </>}
              <PollWidget />
            </Box>
            <FacebookFollow />
          </Box>
        </>
      )}
    </Container>
  );
}

function NewsRow({ items, utm }) {
  return <Box data-news-latest sx={{ display: 'grid', gridTemplateColumns: { xs: 'minmax(0, 1fr)', sm: 'repeat(2, minmax(0, 1fr))', md: 'repeat(3, minmax(0, 1fr))', lg: 'repeat(6, minmax(0, 1fr))' }, gap: 3, '& > *': { minWidth: 0, pb: 2 } }}>{items.map((article) => <SecondaryCard key={article.id || article.slug} article={article} utm={utm} compact />)}</Box>;
}

function TopicSection({ title, section, articles }) {
  return <Box component="section" aria-label={title} sx={{ minWidth: 0 }}>
    <SectionHeader title={title} to={`/nobleseek?category=${section}`} />
    <SecondaryCard article={articles[0]} utm={`portal-${section}`} />
    <Box sx={{ mt: 1.5 }}>{articles.slice(1, 5).map((article) => <Box key={article.id || article.slug} component={Link} to={articleUrl(article.slug)} sx={{ display: 'block', py: 1.5, borderBottom: '1px solid #E8E8E8', textDecoration: 'none', color: 'inherit', '&:hover h3': { color: '#F2631F' } }}>
      <Typography component="h3" className="ns-serif" sx={{ fontSize: 16, fontWeight: 700, lineHeight: 1.6 }}>{article.headline_bn || article.headline}</Typography>
      <Typography variant="caption" className="ns-sans" sx={{ color: '#667085' }}>{timeAgoBn(article.published_at || article.created_at)}</Typography>
    </Box>)}</Box>
  </Box>;
}

// Section / search listing with Load More pagination.
function ListingView({ category, search, cats, initialPage = 1 }) {
  const [items, setItems] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(false);
  const adConfig = useAdConfig();
  useLayoutEffect(() => { if (!loading && !error) completeStoreDocument(); }, [loading, error]);

  const loadPage = useCallback(async (p, append) => {
    if (append) setLoadingMore(true); else setLoading(true);
    setError(false);
    try {
      const res = await fetchNewsList({ category, search, page: p });
      setItems((prev) => (append ? [...prev, ...res.results] : res.results));
      setCount(res.count);
      setPage(p);
    } catch { setError(true); } finally { setLoading(false); setLoadingMore(false); }
  }, [category, search]);

  useEffect(() => {
    setPage(initialPage);
    setItems([]);
    loadPage(initialPage, false);
  }, [category, search, loadPage, initialPage]);

  const title = search ? `অনুসন্ধান: “${search}”` : sectionName(category, cats);
  const hasMore = (initialPage - 1) * 12 + items.length < count;
  const canonicalParams = new URLSearchParams();
  if (initialPage > 1) canonicalParams.set('page', String(initialPage));
  if (category) canonicalParams.set('category', category);
  if (search) canonicalParams.set('search', search);
  const canonical = `${window.location.origin}/nobleseek${canonicalParams.size ? `?${canonicalParams}` : ''}`;

  return (
    <Container maxWidth="lg" sx={{ py: 3, bgcolor: '#FEFEFE', color: '#040D33', overflowWrap: 'anywhere' }}>
      <NewsSeo title={title} description={`${title} — নোবেলসিকের সব খবর এক জায়গায়।`} slug="" canonical={canonical} noindex={Boolean(search) || (!loading && !items.length)} />
      <Box sx={{ maxWidth: 970, mx: 'auto', mb: 4 }}><AdSlot placement="leaderboard" slot={adConfig.slot_shop_subtle} format="auto" minHeight={90} /></Box>
      <Box sx={{ borderBottom: '2px solid #141414', pb: 1, mb: 2.5 }}>
        <Typography component="h1" variant="h4" fontWeight={900} className="ns-serif" sx={{ fontSize: { xs: '1.5rem', md: '2rem' } }}>{title}</Typography>
        <Typography variant="body2" color="text.secondary" className="ns-sans">{count}টি খবর পাওয়া গেছে</Typography>
      </Box>
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          {error && <Box role="alert" sx={{ mb: 2 }}><Typography>খবর লোড করা যায়নি</Typography><Button onClick={() => loadPage(items.length ? page + 1 : 1, !!items.length)}>আবার চেষ্টা করুন</Button></Box>}
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
                        <AdSlot placement="leaderboard" slot={i === 1 ? adConfig.slot_inarticle_1 : adConfig.slot_multiplex} format="auto" minHeight={100} />
                      </Grid>
                    )}
                  </React.Fragment>
                ))}
              </Grid>
              {!items.length && !error && (
                <Box sx={{ textAlign: 'center', py: 6 }}>
                  <Typography variant="h6" className="ns-serif">কোনো খবর পাওয়া যায়নি</Typography>
                  <Button component={Link} to="/nobleseek" variant="outlined" sx={{ mt: 2 }} className="ns-sans">প্রচ্ছদে ফিরুন</Button>
                </Box>
              )}
              {hasMore && (
                <Box sx={{ textAlign: 'center', mt: 3 }}>
                  <Button component={Link} to={`/nobleseek?${new URLSearchParams({ page: String(page + 1), ...(category ? { category } : {}), ...(search ? { search } : {}) })}`}>পরের পৃষ্ঠা</Button>
                  <Button variant="contained" disabled={loadingMore} onClick={() => loadPage(page + 1, true)} sx={{ bgcolor: '#141414' }} className="ns-sans">
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
            <FacebookFollow />
            <AdSlot placement="sidebar" slot={adConfig.slot_sidebar} format="auto" minHeight={250} />
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
  const initialPage = Math.max(1, Number(params.get('page')) || 1);
  const [cats, setCats] = useState([]);

  useEffect(() => {
    fetchNewsCategories().then((c) => { if (Array.isArray(c)) setCats(c); }).catch(() => {});
  }, []);

  // Portal front page when no filter; listing view for section/search.
  // `?search=` (empty) from "সব খবর" buttons shows the full archive.
  if (!category && !search && !params.has('search') && initialPage === 1) return <PortalHome />;
  // A new filter owns fresh state, so pending requests cannot update its results.
  return <ListingView key={JSON.stringify([category, search, initialPage])} category={category} search={search} cats={cats} initialPage={initialPage} />;
}
