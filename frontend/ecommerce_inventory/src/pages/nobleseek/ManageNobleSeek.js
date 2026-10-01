import { useCallback, useEffect, useState } from 'react';
import {
  Box, Typography, Tabs, Tab, Paper, Table, TableHead, TableRow, TableCell, TableBody,
  Button, IconButton, Dialog, DialogTitle, DialogContent, DialogActions, TextField,
  MenuItem, Switch, FormControlLabel, Chip, Stack, Alert, CircularProgress, Grid,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import RefreshIcon from '@mui/icons-material/Refresh';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import { toast } from 'react-toastify';
import useApi from '../../hooks/APIHandler';

const STATUS = ['DRAFT', 'REVIEW', 'PUBLISHED', 'ARCHIVED'];
const EMPTY = {
  id: null, trend: null, category: '', headline: '', headline_bn: '',
  slug: '', excerpt: '', body_html: '', hero_image: '', hero_image_alt: '',
  image_credit: '', source_name: '', source_url: '', tags: '',
  status: 'DRAFT', is_featured: false, is_breaking: false,
  related_product_ids: '', seo_title: '', seo_description: '', fb_post_url: '',
};

function toPayload(f) {
  const splitList = (s) => String(s || '').split(',').map(x => x.trim()).filter(Boolean);
  const splitInts = (s) => String(s || '').split(',').map(x => parseInt(x.trim(), 10)).filter(Number.isFinite);
  // trend is a FK id (or null) — the text field may hold a pasted keyword,
  // which the API would reject as a type error. Coerce numerics, drop text.
  const trendId = f.trend === '' || f.trend == null ? null : Number(f.trend);
  const payload = {
    ...f,
    trend: Number.isFinite(trendId) ? trendId : null,
    category: f.category === '' ? null : Number(f.category),
    tags: Array.isArray(f.tags) ? f.tags : splitList(f.tags),
    seo_keywords: Array.isArray(f.tags) ? f.tags : splitList(f.tags),
    related_product_ids: Array.isArray(f.related_product_ids) ? f.related_product_ids : splitInts(f.related_product_ids),
  };
  // Empty slug must be omitted so the model auto-generates a unique one —
  // posting slug:'' trips DRF SlugField validation on some versions.
  if (!String(payload.slug || '').trim()) delete payload.slug;
  if (payload.id == null) delete payload.id;
  return payload;
}

export default function ManageNobleSeek() {
  const { callApi } = useApi();
  const [tab, setTab] = useState(0);
  const [stats, setStats] = useState(null);
  const [articles, setArticles] = useState([]);
  const [trends, setTrends] = useState([]);
  const [cats, setCats] = useState([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [adCfg, setAdCfg] = useState({});
  const [savingAds, setSavingAds] = useState(false);

  const loadAll = useCallback(async () => {
    setLoading(true);
    const [s, a, t, c, ad] = await Promise.all([
      callApi({ url: 'store/nobleseek/admin/stats/', silent: true }),
      callApi({ url: 'store/nobleseek/admin/articles/', params: { status: statusFilter, search }, silent: true }),
      callApi({ url: 'store/nobleseek/admin/trends/', params: { status: 'NEW' }, silent: true }),
      callApi({ url: 'store/nobleseek/admin/categories/', silent: true }),
      callApi({ url: 'store/nobleseek/admin/ad-config/', silent: true }),
    ]);
    if (s?.status === 200) setStats(s.data.data);
    if (a?.status === 200) setArticles(a.data.data?.results || a.data.data || []);
    if (t?.status === 200) setTrends(t.data.data?.results || t.data.data || []);
    if (c?.status === 200) setCats(c.data.data || []);
    if (ad?.status === 200) setAdCfg(ad.data.data || {});
    setLoading(false);
  }, [callApi, statusFilter, search]);

  useEffect(() => { loadAll(); }, [loadAll]);

  const fetchTrendsNow = async () => {
    const r = await callApi({ url: 'store/nobleseek/admin/trends/fetch/', method: 'POST', body: {} });
    if (r?.status === 200) { toast.success(r.data.message); loadAll(); }
  };

  const createDraft = async (id) => {
    const r = await callApi({ url: `store/nobleseek/admin/trends/${id}/create-draft/`, method: 'POST', body: {} });
    if (r?.status === 200) {
      toast.success(`Draft created${r.data.data?.ai_generated ? ' (AI scaffold)' : ''} — edit & publish`);
      loadAll(); setTab(0);
    }
  };

  const ignoreTrend = async (id) => {
    await callApi({ url: `store/nobleseek/admin/trends/${id}/ignore/`, method: 'POST', body: {} });
    loadAll();
  };

  const openNew = () => { setForm(EMPTY); setDialogOpen(true); };
  const openEdit = (a) => {
    setForm({
      ...EMPTY, ...a, category: a.category || '',
      tags: Array.isArray(a.tags) ? a.tags.join(', ') : (a.tags || ''),
      related_product_ids: Array.isArray(a.related_product_ids) ? a.related_product_ids.join(', ') : '',
    });
    setDialogOpen(true);
  };

  const saveArticle = async () => {
    if (!form.headline.trim() || !form.body_html.trim()) { toast.error('Headline + body required'); return; }
    setSaving(true);
    const payload = toPayload(form);
    const isEdit = !!form.id;
    const r = await callApi({
      url: isEdit ? `store/nobleseek/admin/articles/${form.id}/` : 'store/nobleseek/admin/articles/',
      method: isEdit ? 'PATCH' : 'POST', body: payload, rawError: true,
    });
    setSaving(false);
    if (r?.status === 200 || r?.status === 201) {
      toast.success(isEdit ? 'Article updated' : 'Article created'); setDialogOpen(false); loadAll();
    } else toast.error(r?.data?.message || 'Save failed');
  };

  const archiveArticle = async (id) => {
    if (!window.confirm('Archive this article?')) return;
    await callApi({ url: `store/nobleseek/admin/articles/${id}/`, method: 'DELETE' });
    loadAll();
  };

  const uploadImage = async (file) => {
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const token = localStorage.getItem('token') || sessionStorage.getItem('token') || '';
      const res = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000/api/'}uploads/`, {
        method: 'POST', headers: token ? { Authorization: `Bearer ${token}` } : {}, body: fd,
      });
      const data = await res.json();
      const url = data?.data?.url || data?.url || data?.data?.file || '';
      if (url) { setForm((f) => ({ ...f, hero_image: url })); toast.success('Image uploaded'); }
      else toast.error('Upload failed — paste URL manually');
    } catch { toast.error('Upload failed'); }
    setUploading(false);
  };

  const saveAds = async () => {
    setSavingAds(true);
    const r = await callApi({ url: 'store/nobleseek/admin/ad-config/', method: 'PUT', body: adCfg });
    setSavingAds(false);
    if (r?.status === 200) toast.success('Ad config saved — live instantly');
  };

  return (
    <Box sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
        <Typography variant="h5" fontWeight={800}>NobleSeek News</Typography>
        {stats && (
          <Stack direction="row" spacing={1}>
            <Chip label={`Drafts ${stats.drafts}`} size="small" />
            <Chip label={`Review ${stats.review}`} size="small" color="warning" />
            <Chip label={`Published ${stats.published}`} size="small" color="success" />
            <Chip label={`Trends inbox ${stats.trends_new}`} size="small" color="info" />
            <Chip label={`${stats.total_views} views`} size="small" variant="outlined" />
          </Stack>
        )}
        <Box sx={{ flex: 1 }} />
        <Button startIcon={<RefreshIcon />} onClick={loadAll} disabled={loading} size="small">Reload</Button>
        <Button startIcon={<AddIcon />} variant="contained" onClick={openNew} size="small">New article</Button>
      </Box>

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Articles" /><Tab label={`Trends inbox (${trends.length})`} /><Tab label="Ad slots" />
      </Tabs>

      {tab === 0 && (
        <Paper sx={{ p: 2 }}>
          <Stack direction="row" spacing={1.5} sx={{ mb: 2 }}>
            <TextField size="small" label="Search" value={search} onChange={(e) => setSearch(e.target.value)} />
            <TextField size="small" select label="Status" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} sx={{ minWidth: 140 }}>
              <MenuItem value="">All</MenuItem>{STATUS.map((s) => <MenuItem key={s} value={s}>{s}</MenuItem>)}
            </TextField>
          </Stack>
          {loading ? <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress /></Box> : (
            <Table size="small">
              <TableHead><TableRow><TableCell>Headline</TableCell><TableCell>Status</TableCell><TableCell>Views</TableCell><TableCell>Published</TableCell><TableCell align="right">Actions</TableCell></TableRow></TableHead>
              <TableBody>
                {articles.map((a) => (
                  <TableRow key={a.id} hover>
                    <TableCell sx={{ maxWidth: 420 }}>
                      <Typography variant="body2" fontWeight={700}>{a.headline}</Typography>
                      <Typography variant="caption" color="text.secondary">/{a.slug}</Typography>
                      {a.is_breaking && <Chip size="small" label="BREAKING" color="error" sx={{ ml: 1 }} />}
                      {a.is_featured && <Chip size="small" label="FEATURED" color="secondary" sx={{ ml: 0.5 }} />}
                    </TableCell>
                    <TableCell><Chip size="small" label={a.status} color={a.status === 'PUBLISHED' ? 'success' : 'default'} /></TableCell>
                    <TableCell>{a.view_count}</TableCell>
                    <TableCell><Typography variant="caption">{a.published_at ? new Date(a.published_at).toLocaleString() : '—'}</Typography></TableCell>
                    <TableCell align="right">
                      <Button size="small" component="a" href={`/nobleseek/${a.slug}`} target="_blank">View</Button>
                      <IconButton size="small" onClick={() => openEdit(a)}><EditIcon fontSize="small" /></IconButton>
                      <IconButton size="small" onClick={() => archiveArticle(a.id)}><DeleteIcon fontSize="small" /></IconButton>
                    </TableCell>
                  </TableRow>
                ))}
                {!articles.length && <TableRow><TableCell colSpan={5} align="center">No articles — fetch trends or write manually.</TableCell></TableRow>}
              </TableBody>
            </Table>
          )}
        </Paper>
      )}

      {tab === 1 && (
        <Paper sx={{ p: 2 }}>
          <Box sx={{ display: 'flex', gap: 1, mb: 2, alignItems: 'center' }}>
            <Alert severity="info" sx={{ flex: 1 }}>Google Trends BD + US, refreshed 2x daily by cron. 1-click creates an AI-scaffolded DRAFT — you always edit before publish.</Alert>
            <Button variant="contained" startIcon={<RefreshIcon />} onClick={fetchTrendsNow}>Fetch now</Button>
          </Box>
          <Table size="small">
            <TableHead><TableRow><TableCell>Keyword</TableCell><TableCell>Geo</TableCell><TableCell>Traffic</TableCell><TableCell>Hint</TableCell><TableCell align="right">Actions</TableCell></TableRow></TableHead>
            <TableBody>
              {trends.map((t) => (
                <TableRow key={t.id} hover>
                  <TableCell><Typography fontWeight={700}>{t.keyword}</Typography><Typography variant="caption" color="text.secondary">{t.traffic_label}</Typography></TableCell>
                  <TableCell><Chip size="small" label={t.geo} /></TableCell>
                  <TableCell>{t.traffic_score}</TableCell>
                  <TableCell><Typography variant="caption">{t.category_hint}</Typography></TableCell>
                  <TableCell align="right">
                    <Button size="small" variant="contained" startIcon={<AutoAwesomeIcon />} onClick={() => createDraft(t.id)}>Create draft</Button>
                    <Button size="small" onClick={() => ignoreTrend(t.id)}>Ignore</Button>
                  </TableCell>
                </TableRow>
              ))}
              {!trends.length && <TableRow><TableCell colSpan={5} align="center">Inbox empty — click Fetch now.</TableCell></TableRow>}
            </TableBody>
          </Table>
        </Paper>
      )}

      {tab === 2 && (
        <Paper sx={{ p: 2, maxWidth: 720 }}>
          <Typography variant="h6" fontWeight={800} gutterBottom>AdSense — hybrid density</Typography>
          <Alert severity="warning" sx={{ mb: 2 }}>Shop ads stay OFF (minimal). News detail uses 5 manual slots for max revenue. Get IDs from AdSense → Ads → New ad unit.</Alert>
          <Grid container spacing={2}>
            {[['adsense_client', 'AdSense client (ca-pub-…)'], ['slot_top', 'Top leaderboard slot'], ['slot_inarticle_1', 'In-article slot 1'], ['slot_inarticle_2', 'In-article slot 2'], ['slot_sidebar', 'Sidebar sticky slot'], ['slot_multiplex', 'Multiplex / related slot'], ['slot_shop_subtle', 'Shop subtle slot (optional)']].map(([k, label]) => (
              <Grid item xs={12} sm={6} key={k}>
                <TextField fullWidth size="small" label={label} value={adCfg[k] || ''} onChange={(e) => setAdCfg({ ...adCfg, [k]: e.target.value })} />
              </Grid>
            ))}
          </Grid>
          <Stack sx={{ mt: 2 }} spacing={1}>
            <FormControlLabel control={<Switch checked={!!adCfg.shop_ads_enabled} onChange={(e) => setAdCfg({ ...adCfg, shop_ads_enabled: e.target.checked })} />} label="Shop ads enabled (keep OFF to minimize)" />
            <FormControlLabel control={<Switch checked={!!adCfg.news_detail_max_ads} onChange={(e) => setAdCfg({ ...adCfg, news_detail_max_ads: e.target.checked })} />} label="News detail max ads (ON)" />
            <FormControlLabel control={<Switch checked={!!adCfg.anchor_on_news_only} onChange={(e) => setAdCfg({ ...adCfg, anchor_on_news_only: e.target.checked })} />} label="Anchor/vignette on news only (ON)" />
          </Stack>
          <Button variant="contained" sx={{ mt: 2 }} disabled={savingAds} onClick={saveAds}>{savingAds ? 'Saving…' : 'Save ad config'}</Button>
        </Paper>
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>{form.id ? 'Edit article' : 'New article — write engaging headline + 800 words'}</DialogTitle>
        <DialogContent dividers>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <TextField fullWidth label="Trend keyword (optional)" value={form.trend || ''} onChange={(e) => setForm({ ...form, trend: e.target.value })} size="small" helperText="Paste Google trendy keyword here" />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField fullWidth select label="Category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} size="small">
                <MenuItem value="">—</MenuItem>{cats.map((c) => <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>)}
              </TextField>
            </Grid>
            <Grid item xs={12}><TextField fullWidth label="Headline (Bangla viral + English keyword)" value={form.headline} onChange={(e) => setForm({ ...form, headline: e.target.value })} /></Grid>
            <Grid item xs={12}><TextField fullWidth label="Headline Bangla (display)" value={form.headline_bn} onChange={(e) => setForm({ ...form, headline_bn: e.target.value })} size="small" /></Grid>
            <Grid item xs={12} md={6}><TextField fullWidth label="Slug (auto if empty)" value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} size="small" /></Grid>
            <Grid item xs={12} md={6}><TextField fullWidth select label="Status" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })} size="small">{STATUS.map((s) => <MenuItem key={s} value={s}>{s}</MenuItem>)}</TextField></Grid>
            <Grid item xs={12}><TextField fullWidth label="Excerpt (cards + meta)" value={form.excerpt} onChange={(e) => setForm({ ...form, excerpt: e.target.value })} multiline rows={2} /></Grid>
            <Grid item xs={12}>
              <TextField fullWidth label="Body HTML (600-1000 words, <p><h2><ul> allowed)" value={form.body_html} onChange={(e) => setForm({ ...form, body_html: e.target.value })} multiline rows={12} helperText={`${form.body_html.replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length} words — aim 600+ for 3-4 in-article ad slots`} />
            </Grid>
            <Grid item xs={12} md={8}><TextField fullWidth label="Hero image URL (upload or paste)" value={form.hero_image} onChange={(e) => setForm({ ...form, hero_image: e.target.value })} size="small" /></Grid>
            <Grid item xs={12} md={4}>
              <Button variant="outlined" component="label" disabled={uploading} fullWidth>{uploading ? 'Uploading…' : 'Upload picture'}<input hidden type="file" accept="image/*" onChange={(e) => uploadImage(e.target.files?.[0])} /></Button>
            </Grid>
            <Grid item xs={12} md={6}><TextField fullWidth label="Image alt" value={form.hero_image_alt} onChange={(e) => setForm({ ...form, hero_image_alt: e.target.value })} size="small" /></Grid>
            <Grid item xs={12} md={6}><TextField fullWidth label="Image credit" value={form.image_credit} onChange={(e) => setForm({ ...form, image_credit: e.target.value })} size="small" /></Grid>
            <Grid item xs={12} md={6}><TextField fullWidth label="Source name" value={form.source_name} onChange={(e) => setForm({ ...form, source_name: e.target.value })} size="small" /></Grid>
            <Grid item xs={12} md={6}><TextField fullWidth label="Source URL" value={form.source_url} onChange={(e) => setForm({ ...form, source_url: e.target.value })} size="small" /></Grid>
            <Grid item xs={12} md={6}><TextField fullWidth label="Tags (comma separated)" value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} size="small" /></Grid>
            <Grid item xs={12} md={6}><TextField fullWidth label="Related product IDs (comma, shop funnel)" value={form.related_product_ids} onChange={(e) => setForm({ ...form, related_product_ids: e.target.value })} size="small" /></Grid>
            <Grid item xs={12} md={6}><TextField fullWidth label="SEO title" value={form.seo_title} onChange={(e) => setForm({ ...form, seo_title: e.target.value })} size="small" /></Grid>
            <Grid item xs={12} md={6}><TextField fullWidth label="FB post URL (traffic proof)" value={form.fb_post_url} onChange={(e) => setForm({ ...form, fb_post_url: e.target.value })} size="small" /></Grid>
            <Grid item xs={12}><TextField fullWidth label="SEO description" value={form.seo_description} onChange={(e) => setForm({ ...form, seo_description: e.target.value })} size="small" multiline rows={2} /></Grid>
            <Grid item xs={6}><FormControlLabel control={<Switch checked={!!form.is_featured} onChange={(e) => setForm({ ...form, is_featured: e.target.checked })} />} label="Featured (hero)" /></Grid>
            <Grid item xs={6}><FormControlLabel control={<Switch checked={!!form.is_breaking} onChange={(e) => setForm({ ...form, is_breaking: e.target.checked })} />} label="Breaking" /></Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" disabled={saving} onClick={saveArticle}>{saving ? 'Saving…' : 'Save article'}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
