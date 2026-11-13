import React, { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Alert, Box, Button, Card, CardActionArea, CardContent, Chip, Container, Grid, Pagination, Skeleton, Stack, Typography } from '@mui/material';
import ArrowForwardRounded from '@mui/icons-material/ArrowForwardRounded';
import config from '../../utils/config';
import useSeo from '../useSeo';
import JournalBlocks, { guideContents } from '../components/JournalBlocks';
import AdSlot from '../../nobleseek/ads/AdSlot';
import { useAdConfig } from '../../nobleseek/ads/adsConfig';

const journalEndpoint = `${config.API_URL}store/journal/`;
const endpoint = `${config.API_URL}store/nobleseek/blog/`;
const dateLabel = value => value ? new Date(value).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' }) : '';

export function BlogIndex() {
  const [params, setParams] = useSearchParams();
  const { topic } = useParams();
  const intent=params.get('intent')||'';
  const [topics,setTopics]=useState([]);
  useEffect(()=>{let active=true;axios.get(journalEndpoint+'topics/').then(r=>{if(active&&Array.isArray(r.data))setTopics(r.data);}).catch(()=>{});return()=>{active=false;};},[]);
  const selectedTopic=topics.find(t=>t.slug===topic);
  const changeFilter=(key,value)=>{const next=new URLSearchParams(params);next.delete('page');value?next.set(key,value):next.delete(key);setParams(next);};
  const page = Math.max(1, Number.parseInt(params.get('page'), 10) || 1);
  const [state, setState] = useState({ loading: true, articles: [], count: 0, next: null, error: false });
  const ads = useAdConfig();
  useSeo({ title: `${selectedTopic?.name||'Product guides & stories'} — Fabrything Journal`, description: 'Explore buying guides, product care and practical shopping advice from Fabrything.', path: `/blog${topic?'/topic/'+encodeURIComponent(topic):''}${page > 1 ? `?page=${page}` : ''}`, noindex: !!intent });
  useEffect(() => {
    let active = true;
    setState(s => ({ ...s, loading: true, error: false }));
    axios.get(endpoint, { params: { page, ...(topic?{topic}:{}), ...(intent?{intent}:{}) } }).then(res => {
      const data = res.data?.data || res.data;
      if (active) setState({ loading: false, articles: data.results || [], count: data.count || 0, next: data.next, error: false });
    }).catch(() => { if (active) setState({ loading: false, articles: [], count: 0, error: true }); });
    return () => { active = false; };
  }, [page,topic,intent]);
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
    <nav className="journal-filters" aria-label="Browse journal topics"><Link to="/blog" aria-current={!topic?'page':undefined}>All guides</Link>{topics.filter(t=>t.level<2).map(t=><Link key={t.id} to={'/blog/topic/'+t.slug} aria-current={topic===t.slug?'page':undefined}>{t.name}</Link>)}<label>Guide format<select value={intent} onChange={e=>changeFilter('intent',e.target.value)}><option value="">All formats</option>{['how_to','troubleshooting','buying_guide','comparison','ecosystem'].map(x=><option key={x} value={x}>{x.replaceAll('_',' ')}</option>)}</select></label></nav>{topic&&<Typography component="h2" variant="h4" sx={{mb:3}}>{selectedTopic?.name||topic.replaceAll('-',' ')}</Typography>}<Grid container spacing={3}>
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
    {!state.loading && !state.error && (page > 1 || state.next) && <Pagination aria-label="Journal pages" page={page} count={state.next ? page + 1 : page} onChange={(_, value) => {const next=new URLSearchParams(params);value>1?next.set('page',String(value)):next.delete('page');setParams(next);}}  sx={{ mt: 4 }} />}
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
  const journal=article.journal;
  const contents=journal?guideContents(journal.blocks):[];
  return <div className="journal-page"><div className="journal-topline"><nav aria-label="Breadcrumb"><Link to="/">Home</Link><span>/</span><Link to="/blog">Journal</Link>{journal?.cluster?.map(c=><React.Fragment key={c.slug}><span>/</span><Link to={'/blog/topic/'+c.slug}>{c.name}</Link></React.Fragment>)}</nav><span>Independent choices. Informed readers.</span></div>
    <div className="journal-layout"><aside className="journal-toc"><nav aria-label="Guide contents"><span className="journal-eyebrow">GUIDE CONTENTS</span>{contents.map(c=><a key={c.id} href={'#'+c.id}>{c.title}</a>)}</nav><div className="journal-editorial-note"><strong>Our editorial approach</strong><p>Useful guidance grounded in attributable sources. Product links may earn a commission.</p><Link to="/disclosure">How we fund our guides ↗</Link></div></aside>
    <article className="journal-article"><header className="journal-article-header"><span className="journal-kicker">{journal?journal.intent.replaceAll('_',' '):'PRODUCTS & EVERYDAY LIFE'}</span><h1>{article.headline_bn||article.headline}</h1><p className="journal-deck">{article.excerpt}</p><div className="journal-byline"><span className="journal-avatar" aria-hidden="true">FE</span><div><strong>Fabrything Editorial</strong><p>Updated {dateLabel(article.updated_at||article.published_at)}{article.read_time_minutes?' · '+article.read_time_minutes+' min read':''}</p></div></div></header>
    <aside className="journal-disclosure" aria-label="Affiliate disclosure">{journal?.disclosure||'This guide may include affiliate links. We may earn a commission from purchases. Check the destination website for the updated price.'} <Link to="/disclosure">Read our disclosure</Link></aside>
    {article.hero_image&&!journal?.blocks?.some(b=>b.type==='image'&&b.src===article.hero_image)&&<figure className="journal-hero"><img src={article.hero_image} alt={article.hero_image_alt||article.headline} width="1200" height="675" fetchpriority="high"/>{article.image_credit&&<figcaption>{article.image_credit}</figcaption>}</figure>}
    {journal?<JournalBlocks journal={journal}/>:<div className="journal-prose" dangerouslySetInnerHTML={{__html:article.body_html}}/>}
    {journal?.sources?.length>0&&<section className="journal-sources"><h2>Sources & further reading</h2><ul>{journal.sources.map((s,i)=><li key={i}><a href={s.url} rel="noopener">{s.title} ↗</a></li>)}</ul></section>}
    {!journal&&article.source_name&&<p className="journal-caption">Source: {article.source_url?<a href={article.source_url} rel="noopener">{article.source_name}</a>:article.source_name}</p>}
    <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{my:3}}>{article.tags?.map(tag=><Chip key={tag} label={tag} size="small" variant="outlined"/>)}</Stack><AdSlot slot={ads.slot_inarticle_1} minHeight={100}/>
    </article></div><RelatedGuides slug={slug}/></div>;
}

function RelatedGuides({slug}) {
 const [articles,setArticles]=useState([]);
 useEffect(()=>{let active=true;setArticles([]);axios.get(journalEndpoint+'related/'+encodeURIComponent(slug)+'/').then(r=>{if(active&&Array.isArray(r.data))setArticles(r.data);}).catch(()=>{});return()=>{active=false;};},[slug]);
 return <section className="journal-related"><div className="journal-related-inner"><header><h2>Keep reading</h2><Link to="/blog">Browse all guides →</Link></header>{articles.length?<div className="journal-related-grid">{articles.map(a=><Link className="journal-related-card" to={'/blog/'+encodeURIComponent(a.slug)} key={a.id}>{a.hero_image?<img src={a.hero_image} alt={a.hero_image_alt||a.headline} width="600" height="340" loading="lazy"/>:<div className="journal-card-placeholder"/>}<div><span className="journal-eyebrow">FABRYTHING JOURNAL</span><h3>{a.headline_bn||a.headline}</h3><p>{a.excerpt}</p></div></Link>)}</div>:<p>Explore more useful guides in the <Link to="/blog">journal</Link>, or <Link to="/shop">browse our shop</Link>.</p>}</div></section>;
}
