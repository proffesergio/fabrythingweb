import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Box, Typography, Tabs, Tab, Paper, Table, TableHead, TableRow, TableCell, TableBody,
  Button, IconButton, Dialog, DialogTitle, DialogContent, DialogActions, TextField,
  MenuItem, Switch, FormControlLabel, Chip, Stack, Alert, CircularProgress, Grid,
  Card, CardActionArea, CardContent, Accordion, AccordionSummary, AccordionDetails,
  Tooltip, LinearProgress, Avatar,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import RefreshIcon from '@mui/icons-material/Refresh';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import VisibilityIcon from '@mui/icons-material/Visibility';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import PublishIcon from '@mui/icons-material/Publish';
import SaveIcon from '@mui/icons-material/Save';
import { toast } from 'react-toastify';
import { useLocation } from 'react-router-dom';
import useApi from '../../hooks/APIHandler';
import DeskHome from './tabs/DeskHome';
import TagsManager from './tabs/TagsManager';
import PagesManager from './tabs/PagesManager';
import CommentsManager from './tabs/CommentsManager';
import PushManager from './tabs/PushManager';
import PollsManager from './tabs/PollsManager';
import ShareMenu from './ShareMenu';

// Last-good snapshot so the desk stays usable while the backend sleeps:
// categories render instantly from cache, then refresh in background.
function readSnap(key) {
  try {
    const raw = JSON.parse(localStorage.getItem(key) || 'null');
    return raw && raw.data !== undefined ? raw.data : null;
  } catch { return null; }
}
function writeSnap(key, data) {
  try { localStorage.setItem(key, JSON.stringify({ at: Date.now(), data })); } catch {}
}

// Fail-fast for dashboard loaders — Render's free tier can sleep, and an
// axios call with no timeout would spin the loader forever.
const LOADER_TIMEOUT = 25000;

// Keystroke inputs shouldn't fire API calls — wait for a pause first.
function useDebounced(value, ms = 450) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

const STATUS = ['DRAFT', 'REVIEW', 'PUBLISHED', 'ARCHIVED'];
const STATUS_BN = { DRAFT: 'খসড়া', REVIEW: 'রিভিউ', PUBLISHED: 'প্রকাশিত', ARCHIVED: 'আর্কাইভ' };

// Sidebar deep links (?tab=…) land here without a remount — honour them on
// mount and on every query change.
const TAB_BY_NAME = { dashboard: 0, articles: 1, trends: 2, tags: 3, categories: 4, comments: 5, push: 6, polls: 7, pages: 8, ads: 9 };
function tabFromSearch(search) {
  const q = new URLSearchParams(search || '');
  const t = TAB_BY_NAME[q.get('tab')];
  return { tab: t === undefined ? null : t, breaking: q.get('breaking') === '1' };
}
const EMPTY = {
  id: null, trend: '', category: '', headline: '', headline_bn: '',
  slug: '', excerpt: '', body_html: '', hero_image: '', hero_image_alt: '',
  image_credit: '', source_name: '', source_url: '', tags: '',
  status: 'DRAFT', is_featured: false, is_breaking: false,
  related_product_ids: '', seo_title: '', seo_description: '', fb_post_url: '',
  published_at: '',
};

const stripTags = (s) => String(s || '').replace(/<[^>]+>/g, ' ');
const wordCount = (s) => stripTags(s).split(/\s+/).filter(Boolean).length;
const slugify = (s) => String(s || '').trim().toLowerCase().replace(/[\s_]+/g, '-').replace(/[^\p{L}\p{N}-]+/gu, '').replace(/-+/g, '-').replace(/^-|-$/g, '');
const toLocalInput = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
};

function toPayload(f) {
  const splitList = (s) => String(s || '').split(',').map((x) => x.trim()).filter(Boolean);
  const trendId = f.trend === '' || f.trend == null ? null : Number(f.trend);
  const payload = {
    trend: Number.isFinite(trendId) ? trendId : null,
    category: f.category === '' ? null : Number(f.category),
    headline: f.headline.trim(),
    headline_bn: f.headline_bn.trim(),
    excerpt: f.excerpt,
    body_html: f.body_html,
    hero_image: f.hero_image.trim(),
    hero_image_alt: f.hero_image_alt,
    image_credit: f.image_credit,
    source_name: f.source_name,
    source_url: f.source_url,
    tags: Array.isArray(f.tags) ? f.tags : splitList(f.tags),
    seo_keywords: Array.isArray(f.tags) ? f.tags : splitList(f.tags),
    status: f.status,
    is_featured: !!f.is_featured,
    is_breaking: !!f.is_breaking,
    related_product_ids: [],
    seo_title: f.seo_title,
    seo_description: f.seo_description,
    fb_post_url: f.fb_post_url,
    published_at: f.published_at ? new Date(f.published_at).toISOString() : null,
  };
  if (String(f.slug || '').trim()) payload.slug = f.slug.trim();
  return payload;
}

// What's missing before this article may go live.
function publishGaps(f) {
  const gaps = [];
  if (!f.headline.trim()) gaps.push('শিরোনাম');
  if (wordCount(f.body_html) < 50) gaps.push(`মূল লেখা (এখন ${wordCount(f.body_html)} শব্দ, কমপক্ষে ৫০)`);
  if (!f.hero_image.trim()) gaps.push('প্রধান ছবি');
  if (!f.category) gaps.push('বিভাগ');
  return gaps;
}

export default function ManageNobleSeek() {
  const { callApi } = useApi();
  const location = useLocation();
  const initial = tabFromSearch(location.search);
  const [tab, setTab] = useState(initial.tab ?? 0);
  const [stats, setStats] = useState(() => readSnap('ns_stats'));
  const [articles, setArticles] = useState([]);
  const [trends, setTrends] = useState([]);
  const [cats, setCats] = useState(() => readSnap('ns_cats') || []);
  const [loadError, setLoadError] = useState(false);
  // All five admin endpoints share one staff gate: when they answer 401/403
  // the login itself isn't platform staff (menus still render for domain
  // owners, and stats cards may show stale cache) — say so explicitly with
  // a re-login action instead of a silent empty desk.
  const [authError, setAuthError] = useState(false);
  const [statusFilter, setStatusFilter] = useState('');
  const [catFilter, setCatFilter] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const search = useDebounced(searchInput);
  const [trendSearchInput, setTrendSearchInput] = useState('');
  const trendSearch = useDebounced(trendSearchInput);
  const [trendGeo, setTrendGeo] = useState('');
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [quickCatOpen, setQuickCatOpen] = useState(false);
  const [quickCatName, setQuickCatName] = useState('');
  const [quickSaving, setQuickSaving] = useState(false);

  // Inline rescue for "no categories": create one without leaving the
  // article, then continue publishing with it preselected.
  const quickAddCategory = async () => {
    const name = quickCatName.trim();
    if (!name) return;
    setQuickSaving(true);
    const r = await callApi({
      url: 'store/nobleseek/admin/categories/', method: 'POST',
      body: { name, slug: slugify(name) }, silent: true,
    });
    setQuickSaving(false);
    const id = r?.status === 201 ? (r.data?.data?.id ?? r.data?.id) : null;
    if (r?.status === 200 || r?.status === 201) {
      toast.success('বিভাগ যোগ হয়েছে');
      setQuickCatName('');
      setQuickCatOpen(false);
      await loadAll();
      if (id) setForm((f) => ({ ...f, category: id }));
    } else toast.error('বিভাগ যোগ ব্যর্থ — বিভাগ ট্যাব থেকে চেষ্টা করুন');
  };
  const [adCfg, setAdCfg] = useState({});
  const [savingAds, setSavingAds] = useState(false);
  const [breakingOnly, setBreakingOnly] = useState(() => tabFromSearch(location.search).breaking);
  const [tagDrill, setTagDrill] = useState('');
  const [catForm, setCatForm] = useState({ id: null, name: '', slug: '', description: '', display_order: 0, is_active: true, parent: '' });

  const catName = useCallback((id) => cats.find((c) => c.id === id)?.name || '—', [cats]);

  // callApi identity changes on EVERY render (the shared hook doesn't
  // memoize it), so it must never sit in loadAll's dependency array — that
  // re-fires the loader endlessly and the browser runs out of sockets
  // (ERR_INSUFFICIENT_RESOURCES storm). Route through a ref instead, and
  // guard against overlapping loads.
  const callApiRef = useRef(callApi);
  callApiRef.current = callApi;
  const inflight = useRef(false);

  const loadAll = useCallback(async () => {
    const api = (args) => callApiRef.current({ timeout: LOADER_TIMEOUT, rawError: true, ...args });
    if (inflight.current) return;
    inflight.current = true;
    setLoading(true);
    setLoadError(false);
    setAuthError(false);
    try {
      const params = { status: statusFilter, search };
      if (catFilter) params.category = catFilter;
      const [s, a, t, c, ad] = await Promise.all([
        api({ url: 'store/nobleseek/admin/stats/', silent: true }),
        // Backend admin list has no category/breaking/tag params — fetch a
        // wide page (100) and filter desk-side so presets stay correct.
        api({ url: 'store/nobleseek/admin/articles/', params: { ...params, pageSize: 100 }, silent: true }),
        api({ url: 'store/nobleseek/admin/trends/', params: { status: 'NEW', search: trendSearch, geo: trendGeo }, silent: true }),
        api({ url: 'store/nobleseek/admin/categories/', silent: true }),
        api({ url: 'store/nobleseek/admin/ad-config/', silent: true }),
      ]);
      const all = [s, a, t, c, ad];
      const ok = all.filter((r) => r?.status === 200).length;
      const denied = all.filter((r) => r && (r.status === 401 || r.status === 403)).length;
      if (ok === 0 && denied > 0) setAuthError(true);
      else if (ok === 0) setLoadError(true);
      if (s?.status === 200) { setStats(s.data.data); writeSnap('ns_stats', s.data.data); }
      if (a?.status === 200) {
        let rows = a.data.data?.results || a.data.data || [];
        if (catFilter) rows = rows.filter((r) => String(r.category) === String(catFilter));
        if (breakingOnly) rows = rows.filter((r) => r.is_breaking);
        if (tagDrill) rows = rows.filter((r) => (r.tags || []).includes(tagDrill));
        setArticles(rows);
      }
      if (t?.status === 200) {
        let rows = t.data.data?.results || t.data.data || [];
        if (trendSearch) rows = rows.filter((r) => r.keyword.toLowerCase().includes(trendSearch.toLowerCase()));
        if (trendGeo) rows = rows.filter((r) => r.geo === trendGeo);
        setTrends(rows);
      }
      if (c?.status === 200) { setCats(c.data.data || []); writeSnap('ns_cats', c.data.data || []); }
      if (ad?.status === 200) setAdCfg(ad.data.data || {});
    } finally {
      inflight.current = false;
      setLoading(false);
    }
  }, [statusFilter, catFilter, search, trendSearch, trendGeo, breakingOnly, tagDrill]);

  useEffect(() => { loadAll(); }, [loadAll]);

  // Tab indexes (dashboard-first order, like the reference panel).
  const TAB = TAB_BY_NAME;
  // Sidebar deep links share this route (?tab=…&breaking=…) without
  // remounting — follow the query whenever it changes.
  useEffect(() => {
    const { tab: t, breaking } = tabFromSearch(location.search);
    if (t !== null) setTab(t);
    if (new URLSearchParams(location.search).has('breaking')) setBreakingOnly(breaking);
  }, [location.search]);
  // Dashboard + tag-cloud drills land here with preset filters.
  const drillArticles = (f = {}) => {
    setStatusFilter(f.status || '');
    setBreakingOnly(!!f.breaking);
    setTagDrill(f.tag || '');
    setTab(TAB.articles);
  };
  const gotoTab = (name) => setTab(TAB[name] ?? TAB.dashboard);

  const fetchTrendsNow = async () => {
    const r = await callApi({ url: 'store/nobleseek/admin/trends/fetch/', method: 'POST', body: {} });
    if (r?.status === 200) { toast.success(r.data.message); loadAll(); }
  };

  const createDraft = async (id) => {
    const r = await callApi({ url: `store/nobleseek/admin/trends/${id}/create-draft/`, method: 'POST', body: {} });
    if (r?.status === 200) {
      toast.success(`খসড়া তৈরি${r.data.data?.ai_generated ? ' (AI সহায়তায়)' : ''} — সম্পাদনা করে প্রকাশ করুন`);
      loadAll(); setTab(TAB.articles);
    }
  };

  const ignoreTrend = async (id) => {
    await callApi({ url: `store/nobleseek/admin/trends/${id}/ignore/`, method: 'POST', body: {} });
    loadAll();
  };

  const quickPatch = async (id, patch, label) => {
    const r = await callApi({ url: `store/nobleseek/admin/articles/${id}/`, method: 'PATCH', body: patch, silent: true });
    if (r?.status === 200) { toast.success(label); loadAll(); }
    else toast.error('আপডেট ব্যর্থ হয়েছে');
  };

  const openNew = () => { setForm(EMPTY); setDialogOpen(true); };
  const openEdit = (a) => {
    setForm({
      ...EMPTY, ...a, trend: a.trend || '', category: a.category || '',
      tags: Array.isArray(a.tags) ? a.tags.join(', ') : (a.tags || ''),
      published_at: toLocalInput(a.published_at),
    });
    setDialogOpen(true);
  };

  const saveArticle = async (targetStatus) => {
    const next = { ...form, ...(targetStatus ? { status: targetStatus } : {}) };
    if (next.status === 'PUBLISHED') {
      const gaps = publishGaps(next);
      if (gaps.length) { toast.error(`প্রকাশের আগে ঠিক করুন: ${gaps.join(', ')}`); return; }
    } else if (!next.headline.trim() || wordCount(next.body_html) < 1) {
      toast.error('শিরোনাম + মূল লেখা আবশ্যক'); return;
    }
    setSaving(true);
    const payload = toPayload(next);
    const isEdit = !!form.id;
    const r = await callApi({
      url: isEdit ? `store/nobleseek/admin/articles/${form.id}/` : 'store/nobleseek/admin/articles/',
      method: isEdit ? 'PATCH' : 'POST', body: payload, rawError: true,
    });
    setSaving(false);
    if (r?.status === 200 || r?.status === 201) {
      toast.success(next.status === 'PUBLISHED' ? 'প্রকাশিত হয়েছে' : 'সংরক্ষিত হয়েছে');
      setDialogOpen(false); loadAll();
    } else toast.error(r?.data?.message || 'সংরক্ষণ ব্যর্থ');
  };

  const archiveArticle = async (id) => {
    if (!window.confirm('এই প্রতিবেদন আর্কাইভ করবেন?')) return;
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
      if (url) { setForm((f) => ({ ...f, hero_image: url })); toast.success('ছবি আপলোড হয়েছে'); }
      else toast.error('আপলোড ব্যর্থ — URL হাতে বসান');
    } catch { toast.error('আপলোড ব্যর্থ'); }
    setUploading(false);
  };

  // ── Categories ──
  const saveCategory = async () => {
    if (!catForm.name.trim()) { toast.error('বিভাগের নাম দিন'); return; }
    const payload = {
      name: catForm.name.trim(),
      slug: catForm.slug.trim() || slugify(catForm.name),
      description: catForm.description,
      display_order: Number(catForm.display_order) || 0,
      is_active: !!catForm.is_active,
      parent: catForm.parent === '' ? null : Number(catForm.parent),
    };
    const isEdit = !!catForm.id;
    const r = await callApi({
      url: isEdit ? `store/nobleseek/admin/categories/${catForm.id}/` : 'store/nobleseek/admin/categories/',
      method: isEdit ? 'PATCH' : 'POST', body: payload,
    });
    if (r?.status === 200 || r?.status === 201) {
      toast.success(isEdit ? 'বিভাগ হালনাগাদ হয়েছে' : 'বিভাগ যোগ হয়েছে');
      setCatForm({ id: null, name: '', slug: '', description: '', display_order: 0, is_active: true, parent: '' });
      loadAll();
    }
  };

  const deleteCategory = async (id, name) => {
    if (!window.confirm(`“${name}” বিভাগ মুছবেন? এর খবরগুলো বিভাগহীন হয়ে যাবে।`)) return;
    await callApi({ url: `store/nobleseek/admin/categories/${id}/`, method: 'DELETE' });
    loadAll();
  };

  const saveAds = async () => {
    setSavingAds(true);
    const r = await callApi({ url: 'store/nobleseek/admin/ad-config/', method: 'PUT', body: adCfg });
    setSavingAds(false);
    if (r?.status === 200) toast.success('বিজ্ঞাপন সেটিংস live হয়েছে');
  };

  const words = wordCount(form.body_html);
  const gaps = publishGaps(form);
  const previewUrl = form.slug ? `/nobleseek/${form.slug}` : null;

  return (
    <Box sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2, flexWrap: 'wrap' }}>
        <Typography variant="h5" fontWeight={800}>নোবেলসিক ডেস্ক</Typography>
        <Typography variant="body2" color="text.secondary">প্রতিবেদন লিখুন, রিভিউ করুন, প্রকাশ করুন</Typography>
        <Box sx={{ flex: 1 }} />
        <Button startIcon={<RefreshIcon />} onClick={loadAll} disabled={loading} size="small">রিলোড</Button>
        <Button startIcon={<AddIcon />} variant="contained" onClick={openNew} size="small">নতুন প্রতিবেদন</Button>
      </Box>

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }} variant="scrollable" scrollButtons="auto">
        <Tab label="ড্যাশবোর্ড" />
        <Tab label="প্রতিবেদন" />
        <Tab label={`ট্রেন্ড ইনবক্স (${trends.length})`} />
        <Tab label="ট্যাগ" />
        <Tab label={`বিভাগ (${cats.length})`} />
        <Tab label="মন্তব্য" />
        <Tab label="পুশ" />
        <Tab label="জরিপ" />
        <Tab label="পেজ" />
        <Tab label="বিজ্ঞাপন" />
      </Tabs>

      {authError && (
        <Alert
          severity="error" sx={{ mb: 2 }}
          action={<Button size="small" variant="contained" component="a" href="/admin/auth">পুনরায় লগইন</Button>}
        >
          স্টাফ অ্যাক্সেস প্রয়োজন — এই লগইনটি প্ল্যাটফর্ম Admin/Staff নয় (তাই টেবিল খালি; উপরের সংখ্যাগুলো পুরনো ক্যাশ হতে পারে)। স্টাফ অ্যাকাউন্টে লগইন করুন অথবা Super Admin কে ভূমিকা (role) ঠিক করতে বলুন।
        </Alert>
      )}

      {tab === 0 && (
        <DeskHome cats={cats} onShowArticles={drillArticles} onShowTab={gotoTab} />
      )}

      {tab === 1 && (
        <Paper sx={{ p: 2 }}>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} sx={{ mb: 2 }}>
            <TextField size="small" label="অনুসন্ধান" value={searchInput} onChange={(e) => setSearchInput(e.target.value)} sx={{ minWidth: 200 }} />
            <TextField size="small" select label="স্ট্যাটাস" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} sx={{ minWidth: 150 }}>
              <MenuItem value="">সব</MenuItem>{STATUS.map((s) => <MenuItem key={s} value={s}>{STATUS_BN[s]}</MenuItem>)}
            </TextField>
            <TextField size="small" select label="বিভাগ" value={catFilter} onChange={(e) => setCatFilter(e.target.value)} sx={{ minWidth: 170 }}>
              <MenuItem value="">সব বিভাগ</MenuItem>{cats.map((c) => <MenuItem key={c.id} value={c.id}>{c.parent_name ? `${c.parent_name} › ${c.name}` : c.name}</MenuItem>)}
            </TextField>
            <Chip
              size="small" label="শুধু ব্রেকিং" clickable color={breakingOnly ? 'error' : 'default'}
              variant={breakingOnly ? 'filled' : 'outlined'} onClick={() => setBreakingOnly((v) => !v)}
              sx={{ alignSelf: 'center' }}
            />
            {tagDrill && (
              <Chip size="small" label={`#${tagDrill}`} color="primary" onDelete={() => setTagDrill('')} sx={{ alignSelf: 'center' }} />
            )}
            {(statusFilter || catFilter || searchInput || breakingOnly || tagDrill) && (
              <Button size="small" onClick={() => { setStatusFilter(''); setCatFilter(''); setSearchInput(''); setBreakingOnly(false); setTagDrill(''); }}>ফিল্টার মুছুন</Button>
            )}
          </Stack>
          {loadError && !loading && (
            <Alert severity="warning" sx={{ mb: 2 }} action={<Button size="small" variant="contained" onClick={loadAll}>পুনরায় চেষ্টা</Button>}>
              সার্ভারে পৌঁছানো যাচ্ছে না (Render free tier ঘুমিয়ে থাকলে প্রথমবার ৩০–৬০ সেকেন্ড লাগে)। একটু অপেক্ষা করে পুনরায় চেষ্টা করুন — বিভাগগুলো শেষবারের সংরক্ষিত তালিকা থেকে দেখানো হচ্ছে।
            </Alert>
          )}
          {loading ? <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress /></Box> : (
            <Table size="small">
              <TableHead><TableRow><TableCell>প্রতিবেদন</TableCell><TableCell>বিভাগ</TableCell><TableCell>স্ট্যাটাস</TableCell><TableCell>পঠিত</TableCell><TableCell>হালনাগাদ</TableCell><TableCell align="right">অ্যাকশন</TableCell></TableRow></TableHead>
              <TableBody>
                {articles.map((a) => (
                  <TableRow key={a.id} hover>
                    <TableCell sx={{ maxWidth: 380 }}>
                      <Box sx={{ display: 'flex', gap: 1.25, alignItems: 'center' }}>
                        <Avatar variant="rounded" src={a.hero_image || undefined} sx={{ width: 56, height: 42, bgcolor: '#eee', fontSize: 18 }}>নো</Avatar>
                        <Box sx={{ minWidth: 0 }}>
                          <Typography variant="body2" fontWeight={700} sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 300 }}>{a.headline}</Typography>
                          <Typography variant="caption" color="text.secondary">/{a.slug}</Typography>
                          <Box sx={{ display: 'flex', gap: 0.5, mt: 0.25 }}>
                            {a.is_breaking && <Chip size="small" label="ব্রেকিং" color="error" sx={{ height: 18, fontSize: 10 }} />}
                            {a.is_featured && <Chip size="small" label="ফিচার্ড" color="secondary" sx={{ height: 18, fontSize: 10 }} />}
                          </Box>
                        </Box>
                      </Box>
                    </TableCell>
                    <TableCell><Typography variant="caption">{catName(a.category)}</Typography></TableCell>
                    <TableCell>
                      <Chip
                        size="small" label={STATUS_BN[a.status] || a.status}
                        color={a.status === 'PUBLISHED' ? 'success' : a.status === 'REVIEW' ? 'warning' : 'default'}
                        onClick={() => quickPatch(a.id, { status: a.status === 'PUBLISHED' ? 'DRAFT' : 'PUBLISHED' }, a.status === 'PUBLISHED' ? 'ড্রাফটে ফেরত নেওয়া হয়েছে' : 'প্রকাশিত হয়েছে')}
                        sx={{ cursor: 'pointer' }}
                      />
                    </TableCell>
                    <TableCell>{a.view_count}</TableCell>
                    <TableCell><Typography variant="caption">{a.published_at ? new Date(a.published_at).toLocaleString('bn-BD') : '—'}</Typography></TableCell>
                    <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                      <Tooltip title="প্রিভিউ"><IconButton size="small" component="a" href={`/nobleseek/${a.slug}`} target="_blank"><VisibilityIcon fontSize="small" /></IconButton></Tooltip>
                      <ShareMenu article={a} />
                      <Tooltip title="সম্পাদনা"><IconButton size="small" onClick={() => openEdit(a)}><EditIcon fontSize="small" /></IconButton></Tooltip>
                      <Tooltip title="ফিচার্ড টগল"><span><IconButton size="small" color={a.is_featured ? 'secondary' : 'default'} onClick={() => quickPatch(a.id, { is_featured: !a.is_featured }, 'ফিচার্ড হালনাগাদ')}><PublishIcon fontSize="small" /></IconButton></span></Tooltip>
                      <Tooltip title="মুছুন/আর্কাইভ"><IconButton size="small" onClick={() => archiveArticle(a.id)}><DeleteIcon fontSize="small" /></IconButton></Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
                {!articles.length && <TableRow><TableCell colSpan={6} align="center">কোনো প্রতিবেদন নেই — ট্রেন্ড থেকে খসড়া বানান বা নতুন লিখুন।</TableCell></TableRow>}
              </TableBody>
            </Table>
          )}
        </Paper>
      )}

      {tab === 2 && (
        <Paper sx={{ p: 2 }}>
          <Box sx={{ display: 'flex', gap: 1, mb: 2, alignItems: 'center', flexWrap: 'wrap' }}>
            <Alert severity="info" sx={{ flex: 1, minWidth: 240 }}>ক্রন দিনে ২ বার নতুন কীওয়ার্ড আনে। ১ ক্লিকে খসড়া — প্রকাশের আগে অবশ্যই সম্পাদনা করুন।</Alert>
            <TextField size="small" label="কীওয়ার্ড খুঁজুন" value={trendSearchInput} onChange={(e) => setTrendSearchInput(e.target.value)} />
            <TextField size="small" select label="অঞ্চল" value={trendGeo} onChange={(e) => setTrendGeo(e.target.value)} sx={{ minWidth: 100 }}>
              <MenuItem value="">সব</MenuItem><MenuItem value="BD">BD</MenuItem><MenuItem value="US">US</MenuItem>
            </TextField>
            <Button variant="contained" startIcon={<RefreshIcon />} onClick={fetchTrendsNow}>এখনই আনুন</Button>
          </Box>
          <Table size="small">
            <TableHead><TableRow><TableCell>কীওয়ার্ড</TableCell><TableCell>অঞ্চল</TableCell><TableCell>ট্রাফিক</TableCell><TableCell>হিন্ট</TableCell><TableCell align="right">অ্যাকশন</TableCell></TableRow></TableHead>
            <TableBody>
              {trends.map((t) => (
                <TableRow key={t.id} hover>
                  <TableCell><Typography fontWeight={700}>{t.keyword}</Typography><Typography variant="caption" color="text.secondary">{t.traffic_label}</Typography></TableCell>
                  <TableCell><Chip size="small" label={t.geo} /></TableCell>
                  <TableCell>{t.traffic_score}</TableCell>
                  <TableCell><Typography variant="caption">{t.category_hint}</Typography></TableCell>
                  <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                    <Button size="small" variant="contained" startIcon={<AutoAwesomeIcon />} onClick={() => createDraft(t.id)}>খসড়া</Button>
                    <Button size="small" onClick={() => ignoreTrend(t.id)}>বাদ</Button>
                  </TableCell>
                </TableRow>
              ))}
              {!trends.length && <TableRow><TableCell colSpan={5} align="center">ইনবক্স খালি — “এখনই আনুন” চাপুন।</TableCell></TableRow>}
            </TableBody>
          </Table>
        </Paper>
      )}

      {tab === 3 && (
        <TagsManager onDrillTag={(tag) => drillArticles({ tag })} />
      )}

      {tab === 4 && (
        <Grid container spacing={2}>
          <Grid item xs={12} md={7}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="subtitle1" fontWeight={800} gutterBottom>বিভাগসমূহ (পোর্টাল নেভিগেশন ক্রম)</Typography>
              <Table size="small">
                <TableHead><TableRow><TableCell>ক্রম</TableCell><TableCell>নাম</TableCell><TableCell>সক্রিয়</TableCell><TableCell align="right">অ্যাকশন</TableCell></TableRow></TableHead>
                <TableBody>
                  {cats.map((c) => (
                    <TableRow key={c.id} hover>
                      <TableCell>{c.display_order}</TableCell>
                      <TableCell>
                        <Typography fontWeight={700}>{c.parent_name ? `↳ ${c.name}` : c.name}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          /{c.slug} • {c.article_count ?? 0}টি খবর{c.parent_name ? ` • অধীন: ${c.parent_name}` : ''}
                        </Typography>
                      </TableCell>
                      <TableCell><Switch size="small" checked={!!c.is_active} onChange={async (e) => {
                        await callApi({ url: `store/nobleseek/admin/categories/${c.id}/`, method: 'PATCH', body: { is_active: e.target.checked }, silent: true });
                        loadAll();
                      }} /></TableCell>
                      <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                        <IconButton size="small" onClick={() => setCatForm({ id: c.id, name: c.name, slug: c.slug, description: c.description || '', display_order: c.display_order, is_active: c.is_active, parent: c.parent || '' })}><EditIcon fontSize="small" /></IconButton>
                        <IconButton size="small" onClick={() => deleteCategory(c.id, c.name)}><DeleteIcon fontSize="small" /></IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                  {!cats.length && <TableRow><TableCell colSpan={4} align="center">কোনো বিভাগ নেই।</TableCell></TableRow>}
                </TableBody>
              </Table>
            </Paper>
          </Grid>
          <Grid item xs={12} md={5}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="subtitle1" fontWeight={800} gutterBottom>{catForm.id ? 'বিভাগ সম্পাদনা' : 'নতুন বিভাগ'}</Typography>
              <Stack spacing={1.5}>
                <TextField size="small" fullWidth label="নাম (বাংলা)" value={catForm.name} onChange={(e) => setCatForm({ ...catForm, name: e.target.value, slug: catForm.id ? catForm.slug : slugify(e.target.value) })} />
                <TextField size="small" fullWidth label="স্লাগ (URL)" value={catForm.slug} onChange={(e) => setCatForm({ ...catForm, slug: e.target.value })} helperText={catForm.slug ? `/nobleseek?category=${catForm.slug}` : 'খালি রাখলে নাম থেকে বানানো হবে'} />
                <TextField size="small" fullWidth label="বিবরণ (ঐচ্ছিক)" value={catForm.description} onChange={(e) => setCatForm({ ...catForm, description: e.target.value })} />
                <TextField size="small" fullWidth select label="অভিভাবক বিভাগ (সাব-সেকশন হলে)" value={catForm.parent} onChange={(e) => setCatForm({ ...catForm, parent: e.target.value })}>
                  <MenuItem value="">— মূল বিভাগ —</MenuItem>
                  {cats.filter((c) => !c.parent && c.id !== catForm.id).map((c) => <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>)}
                </TextField>
                <TextField size="small" fullWidth type="number" label="ক্রম (ছোট = আগে)" value={catForm.display_order} onChange={(e) => setCatForm({ ...catForm, display_order: e.target.value })} />
                <FormControlLabel control={<Switch size="small" checked={!!catForm.is_active} onChange={(e) => setCatForm({ ...catForm, is_active: e.target.checked })} />} label="নেভিগেশনে দেখান" />
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Button variant="contained" size="small" onClick={saveCategory}>{catForm.id ? 'হালনাগাদ' : 'যোগ করুন'}</Button>
                  {catForm.id && <Button size="small" onClick={() => setCatForm({ id: null, name: '', slug: '', description: '', display_order: 0, is_active: true, parent: '' })}>বাতিল</Button>}
                </Box>
              </Stack>
            </Paper>
          </Grid>
        </Grid>
      )}

      {tab === 5 && (
        <CommentsManager />
      )}

      {tab === 6 && (
        <PushManager />
      )}

      {tab === 7 && (
        <PollsManager />
      )}

      {tab === 8 && (
        <PagesManager />
      )}

      {tab === 9 && (
        <Paper sx={{ p: 2, maxWidth: 720 }}>
          <Typography variant="h6" fontWeight={800} gutterBottom>বিজ্ঞাপন (Ad Spaces)</Typography>
          <Alert severity="warning" sx={{ mb: 2 }}>সংবাদ পাতায় ৫টি ম্যানুয়াল স্লট = সর্বোচ্চ আয়। ID নিন: AdSense → Ads → New ad unit।</Alert>
          <Grid container spacing={2}>
            {[['adsense_client', 'AdSense client (ca-pub-…)'], ['slot_top', 'Top leaderboard'], ['slot_inarticle_1', 'In-article 1'], ['slot_inarticle_2', 'In-article 2'], ['slot_sidebar', 'Sidebar sticky'], ['slot_multiplex', 'Multiplex'], ['slot_shop_subtle', 'Portal subtle (ঐচ্ছিক)']].map(([k, label]) => (
              <Grid item xs={12} sm={6} key={k}>
                <TextField fullWidth size="small" label={label} value={adCfg[k] || ''} onChange={(e) => setAdCfg({ ...adCfg, [k]: e.target.value })} />
              </Grid>
            ))}
          </Grid>
          <Stack sx={{ mt: 2 }} spacing={1}>
            <FormControlLabel control={<Switch checked={!!adCfg.shop_ads_enabled} onChange={(e) => setAdCfg({ ...adCfg, shop_ads_enabled: e.target.checked })} />} label="Shop ads (বন্ধ রাখুন)" />
            <FormControlLabel control={<Switch checked={!!adCfg.news_detail_max_ads} onChange={(e) => setAdCfg({ ...adCfg, news_detail_max_ads: e.target.checked })} />} label="News max ads (চালু)" />
            <FormControlLabel control={<Switch checked={!!adCfg.anchor_on_news_only} onChange={(e) => setAdCfg({ ...adCfg, anchor_on_news_only: e.target.checked })} />} label="Anchor শুধু নিউজে (চালু)" />
          </Stack>
          <Button variant="contained" sx={{ mt: 2 }} disabled={savingAds} onClick={saveAds}>{savingAds ? 'সংরক্ষণ…' : 'সংরক্ষণ করুন'}</Button>
        </Paper>
      )}

      {/* ── Editor ── */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="lg" fullWidth>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
          {form.id ? 'প্রতিবেদন সম্পাদনা' : 'নতুন প্রতিবেদন'}
          <Chip size="small" label={STATUS_BN[form.status]} color={form.status === 'PUBLISHED' ? 'success' : form.status === 'REVIEW' ? 'warning' : 'default'} />
          {previewUrl && <Button size="small" startIcon={<VisibilityIcon />} component="a" href={previewUrl} target="_blank">প্রিভিউ</Button>}
        </DialogTitle>
        <DialogContent dividers>
          <Grid container spacing={2.5}>
            {/* Main column */}
            <Grid item xs={12} md={7}>
              <Stack spacing={1.75}>
                <TextField fullWidth label="শিরোনাম" value={form.headline} onChange={(e) => setForm({ ...form, headline: e.target.value })} helperText={`${form.headline.length}/255`} />
                <TextField fullWidth size="small" label="বাংলা প্রদর্শন শিরোনাম (ঐচ্ছিক)" value={form.headline_bn} onChange={(e) => setForm({ ...form, headline_bn: e.target.value })} />
                <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
                  <TextField fullWidth size="small" label="স্লাগ (খালি = অটো)" value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} helperText={form.slug ? `/nobleseek/${form.slug}` : 'সংরক্ষণে শিরোনাম থেকে বানানো হবে'} />
                  <Button size="small" variant="outlined" sx={{ mt: 0.5, whiteSpace: 'nowrap' }} onClick={() => setForm({ ...form, slug: slugify(form.headline_bn || form.headline) })} disabled={!form.headline.trim()}>অটো</Button>
                </Box>
                <TextField fullWidth label="সারসংক্ষেপ (কার্ড + SEO)" value={form.excerpt} onChange={(e) => setForm({ ...form, excerpt: e.target.value })} multiline rows={2} helperText={`${form.excerpt.length}/300`} />
                <Box>
                  <TextField fullWidth label="মূল লেখা (HTML: <p> <h2> <ul>)" value={form.body_html} onChange={(e) => setForm({ ...form, body_html: e.target.value })} multiline rows={12} />
                  <Box sx={{ mt: 0.75 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="caption" color={words >= 600 ? 'success.main' : 'text.secondary'}>{words} শব্দ {words >= 600 ? '✓ বিজ্ঞাপনের জন্য প্রস্তুত' : '(লক্ষ্য ৬০০+)'}</Typography>
                      <Typography variant="caption" color="text.secondary">~{Math.max(1, Math.ceil(words / 200))} মিনিটে পড়ুন</Typography>
                    </Box>
                    <LinearProgress variant="determinate" value={Math.min(100, (words / 600) * 100)} sx={{ height: 6, borderRadius: 3, mt: 0.5 }} color={words >= 600 ? 'success' : 'primary'} />
                  </Box>
                </Box>
                <Accordion variant="outlined">
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}><Typography variant="body2" fontWeight={700}>SEO ও ফেসবুক (ঐচ্ছিক)</Typography></AccordionSummary>
                  <AccordionDetails>
                    <Stack spacing={1.5}>
                      <TextField fullWidth size="small" label="SEO শিরোনাম" value={form.seo_title} onChange={(e) => setForm({ ...form, seo_title: e.target.value })} helperText={`${form.seo_title.length}/60`} />
                      <TextField fullWidth size="small" label="SEO বিবরণ" value={form.seo_description} onChange={(e) => setForm({ ...form, seo_description: e.target.value })} multiline rows={2} helperText={`${form.seo_description.length}/160`} />
                      <TextField fullWidth size="small" label="FB পোস্ট URL" value={form.fb_post_url} onChange={(e) => setForm({ ...form, fb_post_url: e.target.value })} />
                    </Stack>
                  </AccordionDetails>
                </Accordion>
              </Stack>
            </Grid>
            {/* Side column */}
            <Grid item xs={12} md={5}>
              <Stack spacing={1.75}>
                <Paper variant="outlined" sx={{ p: 1.5 }}>
                  <Typography variant="body2" fontWeight={800} gutterBottom>প্রধান ছবি {form.hero_image ? '✓' : '— আবশ্যক'}</Typography>
                  {form.hero_image ? (
                    <Box component="img" src={form.hero_image} alt="" sx={{ width: '100%', height: 170, objectFit: 'cover', borderRadius: 1.5, mb: 1 }} />
                  ) : (
                    <Alert severity="warning" sx={{ mb: 1 }}>প্রকাশের আগে ছবি দিন — ছবিহীন খবর প্রকাশ হবে না।</Alert>
                  )}
                  <TextField fullWidth size="small" label="ছবির URL" value={form.hero_image} onChange={(e) => setForm({ ...form, hero_image: e.target.value })} sx={{ mb: 1 }} />
                  <Button variant="outlined" component="label" disabled={uploading} fullWidth size="small">{uploading ? 'আপলোড হচ্ছে…' : 'ছবি আপলোড করুন'}<input hidden type="file" accept="image/*" onChange={(e) => uploadImage(e.target.files?.[0])} /></Button>
                </Paper>
                <Grid container spacing={1.5}>
                  <Grid item xs={12} sm={6}><TextField fullWidth size="small" label="ছবির alt" value={form.hero_image_alt} onChange={(e) => setForm({ ...form, hero_image_alt: e.target.value })} /></Grid>
                  <Grid item xs={12} sm={6}><TextField fullWidth size="small" label="ছবির ক্রেডিট" value={form.image_credit} onChange={(e) => setForm({ ...form, image_credit: e.target.value })} /></Grid>
                  <Grid item xs={12} sm={6}><TextField fullWidth size="small" label="সূত্রের নাম" value={form.source_name} onChange={(e) => setForm({ ...form, source_name: e.target.value })} /></Grid>
                  <Grid item xs={12} sm={6}><TextField fullWidth size="small" label="সূত্রের URL" value={form.source_url} onChange={(e) => setForm({ ...form, source_url: e.target.value })} /></Grid>
                </Grid>
                <Grid container spacing={1.5}>
                  <Grid item xs={12} sm={6}>
                    <TextField fullWidth select size="small" label="বিভাগ *" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                      <MenuItem value="">— বেছে নিন —</MenuItem>{cats.map((c) => <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>)}
                    </TextField>
                    {cats.length === 0 && (
                      <Alert severity="warning" sx={{ mt: 1 }} action={<Button size="small" onClick={loadAll}>আবার লোড</Button>}>
                        বিভাগ তালিকা আসেনি — সার্ভার জেগে উঠলে আবার লোড করুন। বিভাগ ছাড়া প্রকাশ হবে না।
                      </Alert>
                    )}
                    {!quickCatOpen ? (
                      <Button size="small" sx={{ mt: 1 }} onClick={() => setQuickCatOpen(true)}>
                        ＋ তালিকায় না থাকলে এখানেই নতুন বিভাগ যোগ করুন
                      </Button>
                    ) : (
                      <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                        <TextField
                          size="small" fullWidth label="নতুন বিভাগের নাম" value={quickCatName}
                          onChange={(e) => setQuickCatName(e.target.value)}
                          onKeyDown={(e) => { if (e.key === 'Enter') quickAddCategory(); }}
                        />
                        <Button size="small" variant="contained" disabled={quickSaving || !quickCatName.trim()} onClick={quickAddCategory}>
                          {quickSaving ? '…' : 'যোগ'}
                        </Button>
                        <Button size="small" onClick={() => { setQuickCatOpen(false); setQuickCatName(''); }}>✕</Button>
                      </Box>
                    )}
                  </Grid>
                  <Grid item xs={12} sm={6}><TextField fullWidth size="small" label="ট্রেন্ড ID (ঐচ্ছিক)" value={form.trend} onChange={(e) => setForm({ ...form, trend: e.target.value })} /></Grid>
                </Grid>
                <TextField fullWidth size="small" label="ট্যাগ (কমা দিয়ে)" value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} />
                <Box sx={{ display: 'flex', gap: 2 }}>
                  <FormControlLabel control={<Switch size="small" checked={!!form.is_featured} onChange={(e) => setForm({ ...form, is_featured: e.target.checked })} />} label="ফিচার্ড (লিড)" />
                  <FormControlLabel control={<Switch size="small" checked={!!form.is_breaking} onChange={(e) => setForm({ ...form, is_breaking: e.target.checked })} />} label="ব্রেকিং (টিকার)" />
                </Box>
              </Stack>
            </Grid>
          </Grid>
        </DialogContent>
        {/* Publish bar */}
        <DialogActions sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', px: 3, py: 1.75, borderTop: '1px solid #eee', position: 'sticky', bottom: 0, bgcolor: 'background.paper' }}>
          <Box sx={{ display: 'flex', gap: 0.5, border: '1px solid #ddd', borderRadius: 1.5, p: 0.25 }}>
            {STATUS.filter((s) => s !== 'ARCHIVED').map((s) => (
              <Button key={s} size="small" variant={form.status === s ? 'contained' : 'text'} onClick={() => setForm({ ...form, status: s })}>{STATUS_BN[s]}</Button>
            ))}
          </Box>
          <TextField size="small" type="datetime-local" label="শিডিউল" value={form.published_at} onChange={(e) => setForm({ ...form, published_at: e.target.value })} InputLabelProps={{ shrink: true }} helperText="ভবিষ্যৎ = সময় এলে live" sx={{ minWidth: 210 }} />
          {gaps.length > 0 && form.status === 'PUBLISHED' && (
            <Typography variant="caption" color="error">ঘাটতি: {gaps.join(', ')}</Typography>
          )}
          <Box sx={{ flex: 1 }} />
          <Button onClick={() => setDialogOpen(false)}>বাতিল</Button>
          <Button variant="outlined" startIcon={<SaveIcon />} disabled={saving} onClick={() => saveArticle(form.id ? undefined : 'DRAFT')}>{saving ? '…' : 'খসড়া রাখুন'}</Button>
          <Button variant="contained" startIcon={<PublishIcon />} disabled={saving} onClick={() => saveArticle('PUBLISHED')} color="success">{saving ? '…' : 'প্রকাশ করুন'}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
