import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Alert, Box, Button, Chip, CircularProgress, Divider, FormControlLabel, Grid,
  MenuItem, Paper, Stack, Switch, Table, TableBody, TableCell, TableHead,
  TableRow, TextField, Typography, ThemeProvider, createTheme,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import useApi from '../../hooks/APIHandler';

const theme = createTheme({
  palette: {
    mode: 'dark', primary: { main: '#58d6e7' }, secondary: { main: '#e85d4a' },
    background: { default: '#0b1016', paper: '#111a24' },
    text: { primary: '#eef4fa', secondary: '#a7b8c8' }, divider: '#293747',
    warning: { main: '#f2c777' }, success: { main: '#70d8ad' },
  },
  typography: { fontFamily: 'Roboto, "Segoe UI", sans-serif', button: { textTransform: 'none' } },
  components: {
    MuiPaper: { styleOverrides: { root: { backgroundImage: 'none' } } },
    MuiTableCell: { styleOverrides: { root: { borderColor: '#293747' } } },
  },
});
const API = 'store/nobleseek/admin/';
const FIELDS = ['news_site_url', 'ingestion_paused', 'daily_article_limit',
  'require_review_for_automation', 'estimated_text_bytes_per_article', 'estimated_image_bytes_per_article'];
const NUMBERS = ['daily_article_limit', 'estimated_text_bytes_per_article', 'estimated_image_bytes_per_article'];
const LABELS = { seo_title: 'SEO title', seo_description: 'Meta description', hero_image: 'Hero image', hero_image_alt: 'Image alt text' };
const pickPolicy = (value) => Object.fromEntries(FIELDS.map((key) => [key, value[key]]));
const number = (value) => value == null ? '—' : Number(value).toLocaleString();

export function formatBytes(value) {
  if (value == null || !Number.isFinite(Number(value))) return 'Unavailable';
  const bytes = Number(value);
  if (bytes < 1024) return `${number(bytes)} B`;
  const exponent = Math.min(3, Math.floor(Math.log(bytes) / Math.log(1024)));
  return `${(bytes / (1024 ** exponent)).toFixed(2)} ${['B', 'KiB', 'MiB', 'GiB'][exponent]}`;
}

export function storageForecast(textBytes, imageBytes, days) {
  const values = [textBytes, imageBytes, days].map((v) => v === '' ? NaN : Number(v));
  if (values.some((v) => !Number.isSafeInteger(v) || v < 0)) return null;
  return 20 * values[2] * (values[0] + values[1]);
}

export function policyErrors(policy) {
  const errors = {};
  try {
    const url = new URL(policy.news_site_url);
    if (!['http:', 'https:'].includes(url.protocol) || !url.hostname || url.username || url.password ||
        url.search || url.hash || !['', '/'].includes(url.pathname)) throw new Error();
  } catch { errors.news_site_url = 'Use an HTTP(S) origin without a path, credentials, query, or fragment.'; }
  NUMBERS.forEach((key) => {
    if (String(policy[key] ?? '').trim() === '' || !Number.isSafeInteger(Number(policy[key])) || Number(policy[key]) < 0 || Number(policy[key]) > 2147483647) {
      errors[key] = 'Enter a whole number from 0 to 2147483647.';
    }
  });
  return errors;
}

function apiError(response, fallback) {
  if ([401, 403].includes(response?.status)) return 'Staff access required. Sign in with a platform staff account and retry.';
  const data = response?.data;
  if (data?.message) return data.message;
  if (data && typeof data === 'object') {
    const fields = Object.entries(data).filter(([key]) => key !== 'data')
      .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(', ') : typeof value === 'string' ? value : JSON.stringify(value)}`);
    if (fields.length) return fields.join(' · ');
  }
  return fallback;
}

function Panel({ eyebrow, title, children, ...props }) {
  return <Paper variant="outlined" sx={{ p: { xs: 2, md: 2.5 }, borderRadius: 2, height: '100%', boxSizing: 'border-box' }} {...props}>
    <Typography sx={{ fontFamily: 'monospace', fontSize: 10, letterSpacing: 1.5, color: 'text.secondary', mb: 0.5 }}>{eyebrow}</Typography>
    <Typography component="h2" variant="subtitle1" fontWeight={700} sx={{ mb: 2 }}>{title}</Typography>
    {children}
  </Paper>;
}

export default function PublishingOperations({ onEditArticle, onShowArticles }) {
  const { callApi } = useApi();
  const apiRef = useRef(callApi);
  apiRef.current = callApi;
  const mounted = useRef(false);
  const [policy, setPolicy] = useState(null);
  const [saved, setSaved] = useState(null);
  const [operations, setOperations] = useState(null);
  const [policyError, setPolicyError] = useState('');
  const [metricsError, setMetricsError] = useState('');
  const [success, setSuccess] = useState('');
  const [loadingPolicy, setLoadingPolicy] = useState(true);
  const [loadingMetrics, setLoadingMetrics] = useState(true);
  const [saving, setSaving] = useState(false);
  const [forecastDays, setForecastDays] = useState(365);

  const request = useCallback((args) => apiRef.current({ timeout: 25000, rawError: true, silent: true, ...args }), []);
  const loadPolicy = useCallback(async () => {
    setLoadingPolicy(true);
    setPolicyError('');
    try {
      const response = await request({ url: `${API}publishing-settings/` });
      if (!mounted.current) return;
      if (response?.status === 200 && response.data?.data) {
        const value = pickPolicy(response.data.data);
        setPolicy(value); setSaved(value);
      } else setPolicyError(apiError(response, 'Publishing settings could not be loaded. Retry when the server is available.'));
    } catch { if (mounted.current) setPolicyError('Publishing settings could not be loaded. Please retry.'); }
    finally { if (mounted.current) setLoadingPolicy(false); }
  }, [request]);
  const loadMetrics = useCallback(async () => {
    setLoadingMetrics(true);
    setMetricsError('');
    try {
      const response = await request({ url: `${API}operations/` });
      if (!mounted.current) return;
      if (response?.status === 200 && response.data?.data) setOperations(response.data.data);
      else setMetricsError(apiError(response, 'Operations data could not be loaded. Please retry.'));
    } catch { if (mounted.current) setMetricsError('Operations data could not be loaded. Please retry.'); }
    finally { if (mounted.current) setLoadingMetrics(false); }
  }, [request]);
  useEffect(() => {
    mounted.current = true;
    // Independent loaders let policy editing work even if measurements fail.
    loadPolicy(); loadMetrics();
    return () => { mounted.current = false; };
  }, [loadPolicy, loadMetrics]);

  const dirty = !!policy && JSON.stringify(policy) !== JSON.stringify(saved);
  const errors = policy ? policyErrors(policy) : {};
  const change = (key, value) => { setPolicy((current) => ({ ...current, [key]: value })); setSuccess(''); };
  const save = async (event) => {
    event.preventDefault();
    if (!policy || Object.keys(errors).length || saving) return;
    setSaving(true); setPolicyError(''); setSuccess('');
    const body = pickPolicy(policy);
    NUMBERS.forEach((key) => { body[key] = Number(body[key]); });
    body.news_site_url = body.news_site_url.trim().replace(/\/$/, '');
    try {
      const response = await request({ url: `${API}publishing-settings/`, method: 'PATCH', body });
      if (!mounted.current) return;
      if (response?.status === 200 && response.data?.data) {
        const value = pickPolicy(response.data.data);
        setPolicy(value); setSaved(value); setSuccess('Publishing settings saved.');
        loadMetrics();
      } else setPolicyError(apiError(response, 'Save failed. Your edits are preserved; retry to save.'));
    } catch { if (mounted.current) setPolicyError('Save failed. Your edits are preserved; please retry.'); }
    finally { if (mounted.current) setSaving(false); }
  };
  const counts = operations?.counts;
  const production = operations?.production_last_24h;
  const seo = operations?.seo;
  const database = operations?.database;
  const estimate = operations?.storage_estimate;
  const providers = operations?.provider_metrics;
  const forecast = policy ? storageForecast(policy.estimated_text_bytes_per_article, policy.estimated_image_bytes_per_article, Number(forecastDays)) : null;

  return <ThemeProvider theme={theme}>
    <Box sx={{ bgcolor: 'background.default', color: 'text.primary', p: { xs: 1.5, md: 3 }, borderRadius: 2 }}>
      <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" gap={2} sx={{ mb: 3, pb: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Box>
          <Typography sx={{ fontFamily: 'monospace', fontSize: 10, letterSpacing: 1.5, color: 'primary.main' }}>FABRYTHING / EDITORIAL / CONTROL CENTER</Typography>
          <Typography component="h1" variant="h4" fontWeight={700} sx={{ mt: 1 }}>SEO &amp; publishing</Typography>
          <Typography variant="body2" color="text.secondary">Publishing policy, metadata audit and storage planning</Typography>
        </Box>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap alignItems="center">
          <Button variant="outlined" component="a" href="/blog" target="_blank" rel="noopener noreferrer" endIcon={<OpenInNewIcon />}>Open blog</Button>
          <Button variant="outlined" component="a" href="/nobleseek" target="_blank" rel="noopener noreferrer" endIcon={<OpenInNewIcon />}>Open news</Button>
          <Button onClick={loadMetrics} disabled={loadingMetrics} startIcon={<RefreshIcon />}>Refresh metrics</Button>
        </Stack>
      </Stack>
      {metricsError && <Alert severity="error" sx={{ mb: 2 }} action={<Button color="inherit" onClick={loadMetrics} disabled={loadingMetrics}>Retry</Button>}>{metricsError}{operations ? ' Showing the previous snapshot below.' : ' No measurements are available.'}</Alert>}
      {loadingMetrics && <Stack direction="row" spacing={1} sx={{ mb: 2 }} role="status"><CircularProgress size={18} /><Typography variant="body2">Loading measured operations…</Typography></Stack>}
      <Grid container spacing={2} sx={{ mb: 2 }}>
        {[
          ['News articles', counts?.news, 'Stored news · all statuses', 'NEWS'],
          ['Blog articles', counts?.blog, 'Stored blog · all statuses', 'BLOG'],
          ['Created last 24h', production?.created, `${number(production?.news_created)} news · ${number(production?.blog_created)} blog`, '24H'],
          ['Metadata gaps', seo?.articles_with_missing_metadata, 'Live articles requiring attention', 'SEO'],
        ].map(([label, value, detail, badge]) => <Grid item xs={6} lg={3} key={label}>
          <Paper variant="outlined" sx={{ p: 2, borderRadius: 2, height: '100%', boxSizing: 'border-box' }}>
            <Stack direction="row" justifyContent="space-between" gap={1}><Typography variant="caption" color="text.secondary">{label}</Typography><Chip size="small" variant="outlined" color="primary" label={badge} /></Stack>
            <Typography variant="h4" fontWeight={700} sx={{ my: 1, fontVariantNumeric: 'tabular-nums' }}>{number(value)}</Typography>
            <Typography variant="caption" color="text.secondary">{detail}</Typography>
            {onShowArticles && ['NEWS', 'BLOG'].includes(badge) && <Button size="small" onClick={() => onShowArticles(badge)} sx={{ display: 'block', mt: 0.5 }}>Manage {badge.toLowerCase()}</Button>}
          </Paper>
        </Grid>)}
      </Grid>
      {counts && <Stack direction="row" gap={1} flexWrap="wrap" sx={{ mb: 3 }}>
        {['total', 'drafts', 'review', 'published', 'scheduled', 'archived', 'created_today', 'total_views'].map((key) => <Chip key={key} variant="outlined" size="small" label={`${key.replace(/_/g, ' ')}: ${number(counts[key])}`} />)}
        <Chip variant="outlined" size="small" label={`Published last 24h: ${number(production?.published)}`} />
      </Stack>}
      <Grid container spacing={2}>
        <Grid item xs={12} lg={8}>
          <Panel eyebrow="CONFIGURATION" title="Publishing settings">
            {policyError && <Alert severity="error" sx={{ mb: 2 }} action={!policy && <Button color="inherit" onClick={loadPolicy}>Retry</Button>}>{policyError}</Alert>}
            {success && <Alert severity="success" sx={{ mb: 2 }} role="status">{success}</Alert>}
            {loadingPolicy ? <CircularProgress size={24} aria-label="Loading publishing settings" /> : policy && <Box component="form" onSubmit={save} noValidate>
              <Box component="fieldset" disabled={saving} sx={{ border: 0, p: 0, m: 0, minWidth: 0 }}>
                <Stack spacing={2.5}>
                  <TextField fullWidth size="small" label="Canonical news origin" value={policy.news_site_url} onChange={(e) => change('news_site_url', e.target.value)} error={!!errors.news_site_url} helperText={errors.news_site_url || 'Origin only, e.g. https://www.fabrything.com. Changing this does not configure DNS or migrate hosting.'} />
                  <TextField fullWidth size="small" label="Daily article cap" type="number" inputProps={{ min: 0, step: 1 }} value={policy.daily_article_limit} onChange={(e) => change('daily_article_limit', e.target.value)} error={!!errors.daily_article_limit} helperText={errors.daily_article_limit || '0 = unlimited. Counts new articles created today; this is not a hosting quota.'} />
                  <Divider />
                  <FormControlLabel control={<Switch checked={!!policy.ingestion_paused} onChange={(e) => change('ingestion_paused', e.target.checked)} />} label={<Box><Typography variant="body2" fontWeight={700}>Pause new article creation</Typography><Typography variant="caption" color="text.secondary">Stops new manual and automated article creation. Existing articles remain editable; scheduled articles and Facebook publishing are not cancelled.</Typography></Box>} />
                  <FormControlLabel control={<Switch checked={!!policy.require_review_for_automation} onChange={(e) => change('require_review_for_automation', e.target.checked)} />} label={<Box><Typography variant="body2" fontWeight={700}>Require review for automation</Typography><Typography variant="caption" color="text.secondary">Applies only to callers using automation: true: attempts to create published articles are saved for review. This does not enable AI review or change existing articles.</Typography></Box>} />
                  <Grid container spacing={2}>
                    {[['estimated_text_bytes_per_article', 'Text bytes per article'], ['estimated_image_bytes_per_article', 'Image bytes per article']].map(([key, label]) => <Grid item xs={12} sm={6} key={key}>
                      <TextField fullWidth size="small" type="number" inputProps={{ min: 0, step: 1 }} label={label} value={policy[key]} onChange={(e) => change(key, e.target.value)} error={!!errors[key]} helperText={errors[key] || 'Editable planning assumption; not measured usage.'} />
                    </Grid>)}
                  </Grid>
                  <Stack direction="row" gap={1} flexWrap="wrap" justifyContent="flex-end" alignItems="center">
                    <Typography variant="caption" color="text.secondary">{dirty ? 'Unsaved changes' : 'Saved policy'}</Typography>
                    <Button disabled={!dirty || saving} onClick={() => { setPolicy(saved); setPolicyError(''); setSuccess(''); }}>Discard edits</Button>
                    <Button type="submit" variant="outlined" disabled={!dirty || saving || Object.keys(errors).length > 0}>{saving ? 'Saving…' : 'Save settings'}</Button>
                  </Stack>
                </Stack>
              </Box>
            </Box>}
          </Panel>
        </Grid>
        <Grid item xs={12} lg={4}>
          <Panel eyebrow="QUALITY ASSURANCE" title="Metadata audit">
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>Live published articles only. Missing explicit metadata may still have public-page fallbacks.</Typography>
            <Stack spacing={1}>
              {Object.entries(LABELS).map(([key, label]) => <Stack direction="row" justifyContent="space-between" key={key}><Typography variant="body2">Missing {label.toLowerCase()}</Typography><Typography variant="body2" color="warning.main">{number(seo?.missing?.[key])}</Typography></Stack>)}
            </Stack>
            <Divider sx={{ my: 2 }} />
            <Typography variant="caption" color="text.secondary">Up to {seo?.sample_limit ?? 10} affected articles, newest first</Typography>
            <Stack spacing={1.5} sx={{ mt: 1.5 }}>
              {seo?.samples?.map((article) => <Paper key={article.id} variant="outlined" sx={{ p: 1.5, bgcolor: '#0f1821', overflowWrap: 'anywhere' }}>
                <Typography variant="body2" fontWeight={700}>{article.headline}</Typography>
                <Typography variant="caption" color="text.secondary">{article.content_type} · /{article.slug}</Typography>
                <Typography variant="caption" color="warning.main" display="block">Missing: {article.missing_fields.map((key) => LABELS[key] || key).join(', ')}</Typography>
                {onEditArticle && <Button size="small" onClick={() => onEditArticle(article.id)}>Open in editor</Button>}
              </Paper>)}
              {seo && !seo.articles_with_missing_metadata && <Alert severity="success">No missing metadata in live articles.</Alert>}
              {!seo && <Typography variant="body2" color="text.secondary">Audit unavailable until operations data loads.</Typography>}
            </Stack>
          </Panel>
        </Grid>
        <Grid item xs={12} lg={8}>
          <Panel eyebrow="INFRASTRUCTURE" title="Database size & storage planning">
            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid item xs={12} sm={6}><Typography variant="caption" color="text.secondary">Measured database size · {database?.vendor || 'vendor unavailable'}</Typography><Typography variant="h6">{database?.available ? formatBytes(database.size_bytes) : 'Unavailable'}</Typography>{!database?.available && <Typography variant="caption" color="text.secondary">{database?.reason || 'No database measurement received.'}</Typography>}</Grid>
              <Grid item xs={12} sm={6}><Typography variant="caption" color="text.secondary">Current article footprint · saved assumptions</Typography><Typography variant="h6">{formatBytes(estimate?.total_bytes)}</Typography><Typography variant="caption" color="text.secondary">Estimated text: {formatBytes(estimate?.text_bytes)} · images: {formatBytes(estimate?.image_bytes)}</Typography></Grid>
            </Grid>
            <Divider sx={{ mb: 2 }} />
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} justifyContent="space-between" alignItems={{ sm: 'center' }}>
              <Box><Typography fontWeight={700}>+20 articles / day</Typography><Typography variant="caption" color="text.secondary">7,300 articles / year · assumes one hero image per new article</Typography></Box>
              <TextField select size="small" label="Forecast horizon" value={forecastDays} onChange={(e) => setForecastDays(Number(e.target.value))} sx={{ minWidth: 180 }}>{[[30, '30 days'], [365, '1 year']].map(([days, label]) => <MenuItem key={days} value={days}>{label}</MenuItem>)}</TextField>
            </Stack>
            <Paper variant="outlined" sx={{ my: 2, p: 2, bgcolor: '#0f1821' }}>
              <Typography variant="caption" color="text.secondary">Additional estimated content storage over {forecastDays} days{dirty ? ' · preview using unsaved assumptions' : ''}</Typography>
              <Typography variant="h4" color="primary.main" sx={{ fontFamily: 'monospace', mt: 0.5 }}>{formatBytes(forecast)}</Typography>
            </Paper>
            <Typography variant="body2" color="text.secondary">{estimate?.assumptions?.note || 'Text allowance per article and one image allowance per hero URL. Excludes indexes, revisions, inline images, replicas, backups and other application data. Images may be stored externally; this is not measured database usage.'}</Typography>
            <Alert severity="info" sx={{ mt: 2 }}>Capacity and time to quota cannot be determined without your provider plan limits and measured usage. This forecast does not predict request usage, costs or automatic scaling.</Alert>
          </Panel>
        </Grid>
        <Grid item xs={12} lg={4}>
          <Panel eyebrow="EXTERNAL SERVICES" title="Provider telemetry">
            <Chip size="small" label={providers?.available ? 'Connected' : 'Unavailable'} variant="outlined" sx={{ mb: 2 }} />
            <Typography variant="body2" color="text.secondary">{providers?.reason || 'No provider telemetry received.'}</Typography>
            <Table size="small" sx={{ mt: 2 }} aria-label="Provider usage"><TableHead><TableRow><TableCell>Metric</TableCell><TableCell>Reported value</TableCell></TableRow></TableHead><TableBody>
              {[['Storage limit', providers?.storage_limit_bytes == null ? 'Unavailable' : formatBytes(providers.storage_limit_bytes)], ['Requests', providers?.requests == null ? 'Unavailable' : number(providers.requests)], ['Cost', providers?.cost == null ? 'Unavailable' : String(providers.cost)]].map(([label, value]) => <TableRow key={label}><TableCell>{label}</TableCell><TableCell>{value}</TableCell></TableRow>)}
            </TableBody></Table>
          </Panel>
        </Grid>
      </Grid>
      <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 2, fontFamily: 'monospace' }}>Snapshot: {operations?.generated_at ? new Date(operations.generated_at).toLocaleString() : 'Not received'} · Refresh retrieves counts; unsaved settings stay intact.</Typography>
    </Box>
  </ThemeProvider>;
}
