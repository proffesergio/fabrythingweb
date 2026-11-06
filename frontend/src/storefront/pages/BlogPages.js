import React, { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Alert, Box, Button, Card, CardActionArea, CardContent, Chip, Container, Grid, Pagination, Skeleton, Stack, Typography } from '@mui/material';
import ArrowForwardRounded from '@mui/icons-material/ArrowForwardRounded';
import config from '../../utils/config';
import useSeo from '../useSeo';
import AdSlot from '../../nobleseek/ads/AdSlot';
import { useAdConfig } from '../../nobleseek/ads/adsConfig';

const endpoint = `${config.API_URL}store/nobleseek/blog/`;
const dateLabel = value => value ? new Date(value).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' }) : '';

export function BlogIndex() {
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number.parseInt(params.get('page'), 10) || 1);
  const [state, setState] = useState({ loading: true, articles: [], count: 0, next: null, error: false });
  const ads = useAdConfig();
  useSeo({ title: 'Product guides & stories — Fabrything Journal', description: 'Explore buying guides, product care and practical shopping advice from Fabrything.', path: `/blog${page > 1 ? `?page=${page}` : ''}` });
  useEffect(() => {
    let active = true;
    setState(s => ({ ...s, loading: true, error: false }));
    axios.get(endpoint, { params: { page } }).then(res => {
      const data = res.data?.data || res.data;
      if (active) setState({ loading: false, articles: data.results || [], count: data.count || 0, next: data.next, error: false });
    }).catch(() => { if (active) setState({ loading: false, articles: [], count: 0, error: true }); });
    return () => { active = false; };
  }, [page]);
  return <Container maxWidth="lg" sx={{ py: { xs: 4, md: 7 } }}>
    <Box sx={{ borderBottom: '1px solid', borderColor: 'divider', pb: 4, mb: 4 }}>
      <Typography variant="overline" color="primary" sx={{ letterSpacing: '.18em', fontWeight: 800 }}>THE FABRYTHING JOURNAL</Typography>
      <Typography component="h1" variant="h2" sx={{ fontSize: { xs: '2.5rem', md: '4rem' }, maxWidth: 760, my: 1.5 }}>Good choices start<br />with a little knowledge.</Typography>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={3} justifyContent="space-between" alignItems={{ sm: 'center' }}>
        <Typography color="text.secondary" sx={{ maxWidth: 580, lineHeight: 1.8 }}>Product stories, useful buying guides and everyday advice. Take a closer look before you choose.</Typography>
        <Button component={Link} to="/shop" endIcon={<ArrowForwardRounded />} sx={{ flexShrink: 0 }}>Explore the shop</Button>
      </Stack>
    </Box>
    {state.error && <Alert severity="error" action={<Button onClick={() => window.location.reload()}>Retry</Button>}>The journal could not be loaded. Please try again.</Alert>}
    <Grid container spacing={3}>
      {state.loading ? [1, 2, 3].map(n => <Grid item xs={12} sm={6} md={4} key={n}><Skeleton variant="rounded" height={300} /></Grid>) : state.articles.map(article => <Grid item xs={12} sm={6} md={4} key={article.id}>
        <Card sx={{ height: '100%', borderRadius: 3 }}>
          <CardActionArea component={Link} to={`/blog/${encodeURIComponent(article.slug)}`} sx={{ height: '100%', display: 'block' }}>
            {article.hero_image ? <Box component="img" src={article.hero_image} alt={article.hero_image_alt || article.headline} loading="lazy" sx={{ width: '100%', aspectRatio: '16/10', objectFit: 'cover' }} /> : <Box sx={{ aspectRatio: '16/10', bgcolor: 'action.hover', display: 'grid', placeItems: 'center' }}><Typography variant="overline" color="text.secondary">FABRYTHING JOURNAL</Typography></Box>}
            <CardContent sx={{ p: 3 }}>
              <Typography variant="caption" color="text.secondary">{dateLabel(article.published_at)}{article.read_time_minutes ? ` · ${article.read_time_minutes} min read` : ''}</Typography>
              <Typography component="h2" variant="h5" sx={{ my: 1.5, lineHeight: 1.4 }}>{article.headline_bn || article.headline}</Typography>
              <Typography color="text.secondary" variant="body2" sx={{ lineHeight: 1.8 }}>{article.excerpt}</Typography>
              <Typography color="primary" variant="body2" fontWeight={700} sx={{ mt: 2 }}>Read the story →</Typography>
            </CardContent>
          </CardActionArea>
        </Card>
      </Grid>)}
    </Grid>
    {!state.loading && !state.error && !state.articles.length && <Box sx={{ py: 7, textAlign: 'center' }}><Typography variant="h5">Our first stories are on their way.</Typography><Typography color="text.secondary" sx={{ mt: 1 }}>Visit again for product guides and advice from our team.</Typography></Box>}
    {!state.loading && !state.error && (page > 1 || state.next) && <Pagination aria-label="Journal pages" page={page} count={state.next ? page + 1 : page} onChange={(_, value) => setParams(value > 1 ? { page: String(value) } : {})} sx={{ mt: 4 }} />}
    {!state.loading && !state.error && state.articles.length > 0 && <AdSlot slot={ads.slot_multiplex} minHeight={120} />}
  </Container>;
}

export function BlogArticle() {
  const { slug } = useParams();
  const [state, setState] = useState({ loading: true, article: null, error: false, missing: false });
  const ads = useAdConfig();
  const article = state.article;
  useSeo({ title: article ? `${article.seo_title || article.headline} — Fabrything Journal` : 'Product story — Fabrything Journal', description: article?.seo_description || article?.excerpt || 'Product guides and practical advice from Fabrything.', path: `/blog/${encodeURIComponent(slug)}`, noindex: state.missing, image: article?.hero_image, jsonLd: article?.json_ld, type: 'article' });
  useEffect(() => {
    let active = true;
    setState({ loading: true, article: null, error: false, missing: false });
    axios.get(`${endpoint}${encodeURIComponent(slug)}/`).then(res => {
      if (active) setState({ loading: false, article: res.data?.data || res.data, error: false, missing: false });
    }).catch(error => { if (active) setState({ loading: false, article: null, error: true, missing: error.response?.status === 404 }); });
    window.scrollTo(0, 0);
    return () => { active = false; };
  }, [slug]);
  if (state.loading) return <Container maxWidth="md" sx={{ py: 6 }}><Skeleton height={100} /><Skeleton variant="rounded" height={380} sx={{ my: 3 }} /><Skeleton height={200} /></Container>;
  if (!article) return <Container maxWidth="sm" sx={{ py: 10, textAlign: 'center' }}><Typography variant="h4" component="h1">{state.missing ? 'Story not found' : 'Unable to load this story'}</Typography><Typography color="text.secondary" sx={{ my: 2 }}>{state.missing ? 'This article may have moved or is no longer available.' : 'Please try again in a moment.'}</Typography><Button component={Link} to="/blog" variant="outlined">Back to the journal</Button></Container>;
  return <Container maxWidth="md" component="article" sx={{ py: { xs: 4, md: 6 } }}>
    <Button component={Link} to="/blog" sx={{ mb: 3, px: 0 }}>← Fabrything Journal</Button>
    <Typography variant="overline" color="primary" display="block" sx={{ letterSpacing: '.15em' }}>PRODUCTS & EVERYDAY LIFE</Typography>
    <Typography component="h1" variant="h2" sx={{ fontSize: { xs: '2.1rem', md: '3.4rem' }, lineHeight: 1.2, my: 2 }}>{article.headline_bn || article.headline}</Typography>
    <Typography variant="h6" color="text.secondary" fontWeight={400} sx={{ lineHeight: 1.7 }}>{article.excerpt}</Typography>
    <Typography variant="body2" color="text.secondary" sx={{ py: 3 }}>Fabrything Editorial · {dateLabel(article.published_at)} · {article.read_time_minutes || 1} min read</Typography>
    {article.hero_image && <Box component="figure" sx={{ m: 0, mb: 4 }}><Box component="img" src={article.hero_image} alt={article.hero_image_alt || article.headline} fetchPriority="high" sx={{ width: '100%', borderRadius: 3 }} />{article.image_credit && <Typography component="figcaption" variant="caption" color="text.secondary">{article.image_credit}</Typography>}</Box>}
    <AdSlot slot={ads.slot_top} minHeight={90} />
    <Box sx={{ overflowWrap: 'anywhere', fontSize: '1.08rem', lineHeight: 1.95, '& img, & video, & iframe': { maxWidth: '100%', height: 'auto' }, '& h2, & h3': { mt: 4, lineHeight: 1.4 }, '& a': { color: 'primary.main' }, '& table': { display: 'block', overflowX: 'auto', maxWidth: '100%' } }} dangerouslySetInnerHTML={{ __html: article.body_html }} />
    {article.source_name && <Typography variant="body2" color="text.secondary" sx={{ mt: 3 }}>Source: {article.source_url ? <a href={article.source_url} target="_blank" rel="noreferrer">{article.source_name}</a> : article.source_name}</Typography>}
    <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ my: 3 }}>{article.tags?.map(tag => <Chip key={tag} label={tag} size="small" variant="outlined" />)}</Stack>
    <AdSlot slot={ads.slot_inarticle_1} minHeight={100} />
    <Box sx={{ borderTop: '1px solid', borderColor: 'divider', pt: 3, mt: 4 }}><Typography variant="h6">Ready to explore?</Typography><Typography color="text.secondary" sx={{ my: 1 }}>Discover products across the Fabrything shop.</Typography><Button component={Link} to="/shop" endIcon={<ArrowForwardRounded />}>Browse products</Button></Box>
  </Container>;
}
