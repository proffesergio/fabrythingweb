import React, { useMemo, useState } from 'react';
import {
  Alert, Button, Chip, CircularProgress, Dialog, DialogActions,
  DialogContent, DialogContentText, DialogTitle, FormControl, Grid, IconButton,
  MenuItem, Paper, Select, Skeleton, Stack, Switch, TextField, Tooltip, Typography,
} from '@mui/material';
import {
  Add, ArrowOutward, Autorenew, Bolt, CheckCircleOutline, ErrorOutline,
  Inventory2Outlined, PauseCircleOutline, PlayArrow, QueryStats, Refresh,
  ShoppingCartOutlined, SignalCellularAlt, WarningAmber,
} from '@mui/icons-material';
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip as ChartTooltip,
  XAxis, YAxis,
} from 'recharts';
import { Link } from 'react-router-dom';
import useShopControlCenter from './useShopControlCenter';
import './ShopControlCenter.css';

const C = { bg: '#0B1016', panel: '#111A24', panel2: '#172331', border: '#293747', text: '#EEF4FA', muted: '#A7B8C8', cyan: '#58D6E7', coral: '#E85D4A', green: '#70D8AD', amber: '#F2C777', red: '#FF8795' };
const INTERVALS = [
  { label: 'Hourly', value: 60 }, { label: 'Daily', value: 1440 }, { label: 'Weekly', value: 10080 },
];
const EMPTY_ROWS = [];
const MODES = { IMPORT: 'Catalog import', PRICE: 'Price sync', MERCHANT: 'Merchant Center', ANALYTICS: 'Analytics', SEARCH_CONSOLE: 'Search Console' };
const demoJobs = [
  { id: 'd1', mode: 'IMPORT', source_name: 'Fabrilife', category_path: 'Men / Outerwear', interval_minutes: 60, batch_limit: 12, is_paused: false, next_run_at: '2026-11-02T14:00:00Z' },
  { id: 'd2', mode: 'PRICE', source_name: 'Fabrilife', category_path: 'All mapped categories', interval_minutes: 1440, batch_limit: 12, is_paused: false, next_run_at: '2026-11-03T00:00:00Z' },
  { id: 'd3', mode: 'MERCHANT', interval_minutes: 1440, batch_limit: 12, is_paused: true, next_run_at: null },
  { id: 'd4', mode: 'SEARCH_CONSOLE', interval_minutes: 10080, batch_limit: 12, is_paused: false, next_run_at: '2026-11-08T03:00:00Z' },
];
const demoInsights = {
  kpis: { total_orders: 528, total_units: 1378, total_revenue: 362400 },
  inventory_state: 'available',
  inventory_velocity: [
    { variant__product_id: 'p1', product_name: 'Field Jacket · Olive', units: 148, revenue: 118400 },
    { variant__product_id: 'p2', product_name: 'Everyday Canvas Tote', units: 112, revenue: 22400 },
    { variant__product_id: 'p3', product_name: 'Core Tee · Midnight', units: 94, revenue: 32900 },
    { variant__product_id: 'p4', product_name: 'Utility Crossbody', units: 73, revenue: 58400 },
    { variant__product_id: 'p5', product_name: 'Studio Cap · Sand', units: 61, revenue: 18300 },
  ],
  sales_heatmap: Array.from({ length: 30 }, (_, i) => ({ day: new Date(Date.UTC(2026, 9, 3 + i)).toISOString().slice(0, 10), revenue: (i + 4) * 650, orders: [4, 7, 3, 12, 9, 15, 11, 6, 17, 8, 13, 19, 9, 22, 16, 11, 25, 14, 18, 28, 15, 21, 13, 30, 17, 24, 19, 27, 22, 34][i], units: [6, 9, 3, 16, 11, 19, 14, 8, 22, 10, 17, 25, 12, 28, 20, 14, 31, 18, 23, 36, 19, 27, 16, 39, 22, 31, 24, 34, 27, 42][i] })),
  conversion_funnel: [{ stage: 'view_item', count: 8420 }, { stage: 'add_to_cart', count: 1624 }, { stage: 'begin_checkout', count: 814 }, { stage: 'purchase', count: 528 }],
  product_funnels: [
    { item_id: 'p1', item_name: 'Field Jacket · Olive', views: 1290, adds_to_cart: 236, checkouts: 121, purchases: 86 },
    { item_id: 'p2', item_name: 'Everyday Canvas Tote', views: 1104, adds_to_cart: 198, checkouts: 92, purchases: 62 },
    { item_id: 'p3', item_name: 'Core Tee · Midnight', views: 987, adds_to_cart: 165, checkouts: 84, purchases: 53 },
    { item_id: 'p4', item_name: 'Utility Crossbody', views: 874, adds_to_cart: 142, checkouts: 70, purchases: 41 },
  ],
  search_gaps: [{ query: 'linen co-ord set', clicks: 42, impressions: 1860, ctr: 0.0226 }, { query: 'oversized field jacket', clicks: 31, impressions: 1402, ctr: 0.0221 }, { query: 'canvas tote bag', clicks: 18, impressions: 938, ctr: 0.0192 }],
  providers: {
    merchant: { state: 'completed', last_run_at: '2026-11-02T08:40:00Z', result: '48 products submitted' },
    analytics: { state: 'completed', last_run_at: '2026-11-02T08:35:00Z', result: 'Events synced' },
    search_console: { state: 'completed', last_run_at: '2026-11-02T08:15:00Z', result: '30 day query window' },
  },
};
const demoRuns = [
  { id: 'r1', mode: 'PRICE', status: 'COMPLETED', updated_count: 12, failed_count: 0, created_at: '2026-11-02T08:40:00Z', result: '12 prices verified' },
  { id: 'r2', mode: 'MERCHANT', status: 'COMPLETED', updated_count: 12, failed_count: 0, created_at: '2026-11-02T08:35:00Z', result: '12 products submitted' },
  { id: 'r3', mode: 'IMPORT', status: 'PARTIAL', updated_count: 10, failed_count: 2, created_at: '2026-11-02T07:30:00Z', result: '10 products updated · 2 skipped' },
  { id: 'r4', mode: 'SEARCH_CONSOLE', status: 'RUNNING', updated_count: 0, failed_count: 0, created_at: '2026-11-02T07:15:00Z', result: 'Fetching query metrics' },
];

const formatNum = (value) => Number(value || 0).toLocaleString('en-US');
const formatMoney = (value) => `৳${Number(value || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
const dateTime = (value) => value ? new Date(value).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }) : '—';
const relativeDate = (value) => {
  if (!value) return 'No completed run yet';
  const mins = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 60000));
  return mins < 1 ? 'Just now' : mins < 60 ? `${mins}m ago` : `${Math.floor(mins / 60)}h ago`;
};
const providerLabel = (state) => ({ unknown: 'No status data', unconfigured: 'Not connected', empty: 'No data yet', queued: 'Queued', running: 'Syncing', completed: 'Sync successful', failed: 'Sync failed' }[state] || 'Status unavailable');
const providerColor = (state) => ({ completed: C.green, running: C.cyan, scheduled: C.cyan, queued: C.amber, partial: C.amber, paused: C.muted, failed: C.red, unknown: C.muted, unconfigured: C.muted, empty: C.amber }[state] || C.muted);
const providerSummary = (provider) => {
  const result = provider.result;
  if (typeof result === 'string') return result;
  if (result?.submitted_count != null) return `${formatNum(result.submitted_count)} products submitted · approval pending`;
  if (Array.isArray(result?.queries)) return `${formatNum(result.queries.length)} search queries synced`;
  if (Array.isArray(result?.funnel)) return 'Commerce events synced';
  return providerLabel(provider.state);
};
const funnelName = (stage) => ({ view_item: 'Product views', add_to_cart: 'Added to cart', begin_checkout: 'Checkout started', purchase: 'Purchases' }[stage] || String(stage || '').replaceAll('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase()));

function Panel({ eyebrow, title, action, children, className = '' }) {
  return <Paper elevation={0} className={`cc-panel ${className}`}>
    <div className="cc-panel-head">
      <div>{eyebrow && <div className="cc-eyebrow">{eyebrow}</div>}<Typography component="h2" className="cc-panel-title">{title}</Typography></div>
      {action && <div className="cc-panel-action">{action}</div>}
    </div>
    {children}
  </Paper>;
}

function Metric({ icon: Icon, label, value, sub, accent = C.cyan, foot }) {
  return <Paper elevation={0} className="cc-metric" style={{ '--metric-accent': accent }}>
    <div className="cc-metric-top"><span>{label}</span><span className="cc-metric-icon"><Icon fontSize="small" /></span></div>
    <strong className="cc-metric-value">{value}</strong>
    <div className="cc-metric-bottom"><span>{sub}</span>{foot && <b>{foot}</b>}</div>
  </Paper>;
}

function StatePill({ state }) {
  const color = providerColor(state);
  return <span className="cc-state" style={{ '--state-color': color }}><i />{String(state || 'unknown').toUpperCase()}</span>;
}

function EmptyPanel({ children }) {
  return <div className="cc-empty"><QueryStats /><span>{children}</span></div>;
}

function LiveLoading() {
  return <div className="cc-loading" aria-label="Loading live control center">
    <Skeleton variant="rounded" height={54} /><Skeleton variant="rounded" height={88} />
    <Grid container spacing={1.5}><Grid item xs={12} md={8}><Skeleton variant="rounded" height={290} /></Grid><Grid item xs={12} md={4}><Skeleton variant="rounded" height={290} /></Grid></Grid>
    <Skeleton variant="rounded" height={280} />
  </div>;
}

export default function ShopControlCenter() {
  const [demoMode, setDemoMode] = useState(false);
  const [jobDialogOpen, setJobDialogOpen] = useState(false);
  const [draft, setDraft] = useState({ mode: 'ANALYTICS', source: '', category_path: '', target_category: '', interval_minutes: 1440, batch_limit: 12 });
  const [draftError, setDraftError] = useState('');
  const {
    insights: liveInsights, jobs: liveJobs, runs: liveRuns, loading, refreshing,
    error, jobsError, runsError, actionError, pendingAction, lastUpdatedAt,
    refresh, performJobAction, saveJob,
  } = useShopControlCenter({ enabled: !demoMode });
  const data = demoMode ? demoInsights : liveInsights;
  const jobs = demoMode ? demoJobs : liveJobs;
  const runs = demoMode ? demoRuns : liveRuns;
  const sales = data?.sales_heatmap || EMPTY_ROWS;
  const velocity = data?.inventory_velocity || [];
  const funnel = Array.isArray(data?.conversion_funnel) ? data.conversion_funnel : [];
  const gaps = data?.search_gaps || [];
  const orders = data?.kpis?.total_orders ?? sales.reduce((sum, day) => sum + Number(day.orders || 0), 0);
  const units = data?.kpis?.total_units;
  const revenue = data?.kpis?.total_revenue;
  const orderStage = funnel.find((item) => /purchase/i.test(item.stage || ''));
  const visitStage = funnel.find((item) => /view_item/i.test(item.stage || ''));
  const conversion = orderStage && visitStage && Number(visitStage.count) > 0
    ? `${(Number(orderStage.count) / Number(visitStage.count) * 100).toFixed(1)}%` : '—';
  const maxOrders = Math.max(1, ...sales.map((item) => Number(item.orders || 0)));
  const maxUnits = Math.max(1, ...velocity.map((item) => Number(item.units || 0)));
  const heatColumns = Math.min(10, Math.max(5, Math.ceil(Math.sqrt(Math.max(sales.length, 1) * 2))));
  const chartData = useMemo(() => sales.map((item) => ({ ...item, label: item.day ? item.day.slice(5) : '' })), [sales]);
  const productFunnels = Array.isArray(data?.product_funnels) ? data.product_funnels : [];
  const providerRows = [
    ['merchant', 'Google Merchant Center'], ['analytics', 'Google Analytics'], ['search_console', 'Search Console'],
  ].map(([key, label]) => ({ key, label, ...(data?.providers?.[key] || { state: data ? 'unconfigured' : 'unknown' }) }));
  const taskForProvider = (key) => jobs.find((job) => ({ merchant: 'MERCHANT', analytics: 'ANALYTICS', search_console: 'SEARCH_CONSOLE' }[key] === job.mode));

  const runJob = (job) => demoMode ? null : performJobAction(job, 'run');
  const togglePause = (job) => demoMode ? null : performJobAction(job, job.is_paused ? 'resume' : 'pause');
  const updateInterval = (job, interval) => demoMode ? null : saveJob({ interval_minutes: Number(interval) }, job.id);
  const closeJobDialog = () => { if (!pendingAction) { setJobDialogOpen(false); setDraftError(''); } };
  const createJob = async () => {
    const needsSource = ['IMPORT', 'PRICE'].includes(draft.mode);
    if (needsSource && !draft.source) { setDraftError('Enter the source ID used by the catalog.'); return; }
    if (draft.mode === 'IMPORT' && (!draft.category_path.trim() || !draft.target_category)) {
      setDraftError('Catalog import needs a source, category path, and target category ID.'); return;
    }
    if (!Number.isInteger(Number(draft.batch_limit)) || Number(draft.batch_limit) < 1 || Number(draft.batch_limit) > 12) {
      setDraftError('Batch limit must be a whole number from 1 to 12.'); return;
    }
    const payload = {
      mode: draft.mode,
      source: needsSource ? Number(draft.source) : null,
      interval_minutes: Number(draft.interval_minutes),
      batch_limit: Number(draft.batch_limit),
    };
    if (draft.mode === 'IMPORT') {
      payload.category_path = draft.category_path.trim();
      payload.target_category = Number(draft.target_category);
    }
    if (await saveJob(payload)) { setJobDialogOpen(false); setDraftError(''); }
  };

  if (loading && !demoMode && !liveInsights) return <div className="cc-root"><LiveLoading /></div>;

  return <div className={`cc-root ${demoMode ? 'cc-demo' : ''}`}>
    {demoMode && <div className="cc-demo-banner"><Bolt fontSize="small" /> DEMO PREVIEW <span>Deterministic sample data · task controls disabled · never sent to live services</span></div>}

    <header className="cc-header">
      <div className="cc-heading">
        <div className="cc-breadcrumb">FABRYTHING / SHOP / <b>CONTROL CENTER</b></div>
        <div className="cc-title-line"><div><Typography component="h1" className="cc-title">Shop Control Center</Typography><p className="cc-subtitle">Live commerce telemetry &amp; sync operations</p></div><Chip className="cc-live-pill" icon={<span className="cc-live-dot" />} label={demoMode ? 'DEMO MODE' : error ? 'CONNECTION ISSUE' : 'LIVE MONITORING'} /></div>
      </div>
      <div className="cc-toolbar">
        <div className="cc-demo-control"><span>Demo data</span><Switch size="small" checked={demoMode} onChange={(event) => setDemoMode(event.target.checked)} inputProps={{ role: 'switch', 'aria-label': 'Show demo data' }} /></div>
        <Button className="cc-refresh" disabled={demoMode || refreshing} startIcon={refreshing ? <CircularProgress size={14} /> : <Refresh />} onClick={() => refresh()}>{refreshing ? 'Updating' : 'Refresh'}</Button>
        <Button className="cc-overview-link" component={Link} to="/admin/shop" endIcon={<ArrowOutward />}>Overview</Button>
      </div>
    </header>

    <div className="cc-freshness">
      <span className="cc-fresh-led" />
      {demoMode ? 'Sample snapshot · fixed demo data' : error ? liveInsights ? 'Live insights unavailable · last snapshot retained' : 'Live source unavailable' : `Live data checked ${lastUpdatedAt ? dateTime(lastUpdatedAt) : '—'}`}
      <span className="cc-fresh-sep">/</span>
      <span>30 DAY WINDOW</span>
      <span className="cc-fresh-spacer" />
      <span>{demoMode ? 'PREVIEW' : refreshing ? 'REFRESHING' : 'AUTO REFRESH 60S'}</span>
    </div>

    {!demoMode && error && <Alert severity="warning" className="cc-alert" action={<Button size="small" onClick={() => refresh()}>Retry</Button>}>{liveInsights ? 'The latest live snapshot could not be refreshed. Showing the last successful response.' : 'Live insights are unavailable. Metrics below remain empty until a live response arrives.'}</Alert>}
    {!demoMode && jobsError && <Alert severity="warning" className="cc-alert" action={<Button size="small" onClick={() => refresh()}>Retry</Button>}>Sync jobs could not be loaded. Task controls are unavailable.</Alert>}
    {!demoMode && actionError && <Alert severity="error" className="cc-alert">{actionError.message || 'The requested task action failed. The server state has not been changed in this view.'}</Alert>}

    <section className="cc-metrics" aria-label="Shop metrics">
      <Metric icon={ShoppingCartOutlined} label="Orders · 30 days" value={data?.kpis?.total_orders != null || sales.length ? formatNum(orders) : '—'} sub={sales.length ? `${sales.length} daily records` : error ? 'Live metric unavailable' : 'No sales records'} accent={C.cyan} />
      <Metric icon={Inventory2Outlined} label="Units moved" value={units !== undefined && units !== null ? formatNum(units) : '—'} sub={velocity.length ? 'Full-window product units' : data?.inventory_state === 'empty' ? 'Inventory is empty' : error ? 'Live metric unavailable' : 'No velocity data'} accent={C.green} />
      <Metric icon={SignalCellularAlt} label="Tracked revenue" value={revenue !== undefined && revenue !== null ? formatMoney(revenue) : '—'} sub={revenue !== undefined && revenue !== null ? 'Full-window order revenue' : error ? 'Live metric unavailable' : 'No revenue records'} accent={C.coral} />
      <Metric icon={QueryStats} label="View → purchase" value={conversion} sub={orderStage ? 'Product-view / purchase events' : 'No funnel data'} accent={C.amber} />
    </section>

    <Grid container spacing={1.5} className="cc-grid-row">
      <Grid item xs={12} lg={7}>
        <Panel eyebrow="SALES ACTIVITY" title="Revenue overview" action={<span className="cc-panel-meta">DAILY · LAST 30 DAYS</span>}>
          {sales.length ? <div className="cc-chart-wrap">
            <div className="cc-chart-legend"><span><i className="cc-legend-cyan" /> Revenue</span><span><i className="cc-legend-coral" /> Orders</span></div>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 8, left: -20, bottom: 0 }}>
                <defs><linearGradient id="ccOrdersFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={C.cyan} stopOpacity={0.22} /><stop offset="95%" stopColor={C.cyan} stopOpacity={0} /></linearGradient></defs>
                <CartesianGrid stroke={C.border} strokeDasharray="3 5" vertical={false} />
                <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fill: C.muted, fontSize: 10 }} minTickGap={24} />
                <YAxis yAxisId="revenue" axisLine={false} tickLine={false} tick={{ fill: C.muted, fontSize: 10 }} tickFormatter={(value) => `৳${Number(value || 0).toLocaleString('en-US', { notation: 'compact' })}`} />
                <YAxis yAxisId="orders" orientation="right" axisLine={false} tickLine={false} allowDecimals={false} width={32} tick={{ fill: C.coral, fontSize: 10 }} />
                <ChartTooltip contentStyle={{ background: C.panel2, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text }} labelStyle={{ color: C.muted }} formatter={(value, name) => [name === 'Revenue' ? formatMoney(value) : formatNum(value), name]} />
                <Area yAxisId="revenue" type="monotone" dataKey="revenue" name="Revenue" stroke={C.cyan} strokeWidth={2} fill="url(#ccOrdersFill)" isAnimationActive={false} />
                <Area yAxisId="orders" type="monotone" dataKey="orders" name="Orders" stroke={C.coral} strokeWidth={1.5} fill="none" isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div> : <EmptyPanel>{error ? 'Live order activity is unavailable.' : 'Sales data will appear after orders are recorded.'}</EmptyPanel>}
        </Panel>
      </Grid>
      <Grid item xs={12} lg={5}>
        <Panel eyebrow="DAILY DISTRIBUTION" title="Sales heatmap" action={<span className="cc-panel-meta">ORDERS / DAY</span>}>
          {sales.length ? <div className="cc-heatmap-wrap">
            <div className="cc-heatmap" style={{ '--heat-cols': heatColumns }}>
              {sales.map((day, i) => {
                const value = Number(day.orders || 0);
                const intensity = Math.min(1, value / maxOrders);
                return <Tooltip key={`${day.day}-${i}`} title={`${day.day || 'Date unavailable'} · ${formatNum(value)} orders`} arrow><div className="cc-heat-cell" style={{ '--heat': intensity }} aria-label={`${day.day}: ${value} orders`} /></Tooltip>;
              })}
            </div>
            <div className="cc-heatmap-scale"><span>Less</span><i /><i /><i /><i /><span>More</span></div>
            <div className="cc-heatmap-foot"><span>{sales[0]?.day || '—'}</span><span>Each cell represents one reported day</span><span>{sales[sales.length - 1]?.day || '—'}</span></div>
          </div> : <EmptyPanel>{error ? 'The heatmap requires a live sales response.' : 'Daily sales distribution is not available yet.'}</EmptyPanel>}
        </Panel>
      </Grid>
    </Grid>

    <Grid container spacing={1.5} className="cc-grid-row">
      <Grid item xs={12} lg={7}>
        <Panel eyebrow="PRODUCT VELOCITY" title="Fastest moving inventory" action={<Button component={Link} to="/admin/manage/product" className="cc-text-button" endIcon={<ArrowOutward />}>Inventory</Button>}>
          {velocity.length ? <div className="cc-velocity-list">
            {velocity.slice(0, 6).map((item, i) => {
              const percent = Math.round(Number(item.units || 0) / maxUnits * 100);
              return <div className="cc-velocity-row" key={`${item.variant__product_id || item.product_name}-${i}`}>
                <span className="cc-rank">{String(i + 1).padStart(2, '0')}</span>
                <span className="cc-product-name" title={item.product_name}>{item.product_name || `Product ${item.variant__product_id || '—'}`}</span>
                <div className="cc-velocity-track"><span style={{ width: `${percent}%` }} /></div>
                <span className="cc-velocity-units">{formatNum(item.units)}<small> units</small></span>
                <span className="cc-velocity-revenue">{formatMoney(item.revenue)}</span>
              </div>;
            })}
          </div> : <EmptyPanel>{data?.inventory_state === 'empty' ? 'No inventory is available to measure.' : error ? 'Inventory velocity is unavailable.' : 'Product velocity will appear after sales are recorded.'}</EmptyPanel>}
          {!!velocity.length && <div className="cc-panel-foot"><span>Sorted by units sold in reporting window</span><span>Revenue reflects returned data</span></div>}
        </Panel>
      </Grid>
      <Grid item xs={12} lg={5}>
        <Panel eyebrow="CHECKOUT SIGNALS" title="Conversion funnel" action={<span className="cc-panel-meta">REPORTED EVENTS</span>}>
          {funnel.length ? <div className="cc-funnel-list">
            {funnel.map((stage, i) => {
              const max = Math.max(1, ...funnel.map((row) => Number(row.count || 0)));
              const percent = Number(stage.count || 0) / max * 100;
              return <div className="cc-funnel-row" key={`${stage.stage}-${i}`}><div><span>{String(i + 1).padStart(2, '0')}</span><b>{funnelName(stage.stage)}</b><strong>{formatNum(stage.count)}</strong></div><div className="cc-funnel-track"><i style={{ width: `${percent}%`, '--bar-color': i === funnel.length - 1 ? C.coral : C.cyan }} /></div></div>;
            })}
          </div> : <EmptyPanel>{error ? 'Funnel data is unavailable.' : 'Conversion events are not configured or have no data.'}</EmptyPanel>}
          {funnel.length > 0 && <div className="cc-panel-foot"><span>Stage counts are reported by connected analytics</span></div>}
        </Panel>
      </Grid>
    </Grid>

    <Panel eyebrow="PRODUCT DROP-OFF" title="Product conversion signals">
      {productFunnels.length ? <div className="cc-table-scroll"><table className="cc-table cc-gap-table"><thead><tr><th>Product</th><th>Views</th><th>Added to cart</th><th>Checkout</th><th>Purchases</th><th>View → purchase</th></tr></thead><tbody>
        {productFunnels.map((item, index) => <tr key={`${item.item_id}-${index}`}><td>{item.item_name || item.item_id || 'Unnamed product'}</td><td>{formatNum(item.views)}</td><td>{formatNum(item.adds_to_cart)}</td><td>{formatNum(item.checkouts)}</td><td>{formatNum(item.purchases)}</td><td>{Number(item.views) > 0 ? `${(Number(item.purchases || 0) / Number(item.views) * 100).toFixed(1)}%` : '—'}</td></tr>)}
      </tbody></table></div> : <EmptyPanel>Per-product drop-off appears after connected analytics reports item events.</EmptyPanel>}
    </Panel>

    <Panel eyebrow="AUTOMATION" title="Sync task control" action={<>
      <span className="cc-panel-meta">{jobsError ? 'TASK LIST UNAVAILABLE' : `${jobs.length} TASK${jobs.length === 1 ? '' : 'S'} CONFIGURED`}</span>
      <Button className="cc-add-task" size="small" startIcon={<Add />} disabled={demoMode || !!pendingAction || jobsError} onClick={() => setJobDialogOpen(true)}>Add task</Button>
    </>}>
      {jobs.length ? <div className="cc-table-scroll"><table className="cc-table cc-jobs-table"><thead><tr><th>Task / source</th><th>Cadence</th><th>Next run</th><th>State</th><th><span className="cc-sr-only">Task actions</span></th></tr></thead>
        <tbody>{jobs.map((job) => {
          const pending = pendingAction?.startsWith(`${job.id}:`);
          const cadence = INTERVALS.find((option) => option.value === Number(job.interval_minutes));
          return <tr key={job.id}>
            <td><div className="cc-task-name"><span className="cc-task-icon"><Autorenew fontSize="small" /></span><div><b>{MODES[job.mode] || job.mode || 'Sync task'}</b><small>{job.source_name || job.category_path || (job.mode === 'SEARCH_CONSOLE' ? 'Search Console' : 'Provider task')}</small></div></div></td>
            <td><FormControl size="small" className="cc-cadence"><Select value={cadence?.value || Number(job.interval_minutes) || 1440} inputProps={{ 'aria-label': `Schedule ${MODES[job.mode] || job.mode}` }} onChange={(event) => updateInterval(job, event.target.value)} disabled={demoMode || !!pendingAction || jobsError}>
              {INTERVALS.map((option) => <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>)}
              {!cadence && <MenuItem value={Number(job.interval_minutes)}>{job.interval_minutes} min</MenuItem>}
            </Select></FormControl></td>
            <td><span className="cc-time-cell">{job.next_run_at ? dateTime(job.next_run_at) : job.is_paused ? 'Paused' : 'Not scheduled'}</span></td>
        <td><StatePill state={job.is_paused ? 'paused' : 'scheduled'} /></td>
            <td><div className="cc-row-actions">
              <Button size="small" className="cc-run-button" startIcon={pending && pendingAction.endsWith(':run') ? <CircularProgress size={13} /> : <PlayArrow />} disabled={demoMode || !!pendingAction || jobsError} onClick={() => runJob(job)}>Run now</Button>
              <Tooltip title={job.is_paused ? 'Resume task' : 'Pause task'}><span><IconButton size="small" aria-label={job.is_paused ? `Resume ${MODES[job.mode] || 'task'}` : `Pause ${MODES[job.mode] || 'task'}`} disabled={demoMode || !!pendingAction || jobsError} onClick={() => togglePause(job)}>{job.is_paused ? <PlayArrow fontSize="small" /> : <PauseCircleOutline fontSize="small" />}</IconButton></span></Tooltip>
            </div></td>
          </tr>;
        })}</tbody></table></div> : <EmptyPanel>{jobsError ? 'Task controls are hidden until the live task list can be loaded.' : 'No sync tasks have been configured.'}</EmptyPanel>}
      {demoMode && <div className="cc-table-note">Demo tasks are examples. Scheduling and run controls are disabled.</div>}
    </Panel>

    <Grid container spacing={1.5} className="cc-grid-row">
      <Grid item xs={12} lg={5}>
        <Panel eyebrow="CONNECTED SOURCES" title="Provider status" action={<span className="cc-panel-meta">AUTHENTICATED SYNC</span>}>
          <div className="cc-provider-list">{providerRows.map((provider) => {
            const task = taskForProvider(provider.key);
            const state = provider.state || 'unconfigured';
            const statusColor = providerColor(state);
            return <div className="cc-provider-row" key={provider.key}>
              <div className="cc-provider-left"><span className="cc-provider-mark" style={{ '--provider-color': statusColor }}>{state === 'failed' ? <ErrorOutline /> : state === 'completed' ? <CheckCircleOutline /> : state === 'unconfigured' ? <WarningAmber /> : <Autorenew />}</span><div><b>{provider.label}</b><small>{providerSummary(provider)}</small></div></div>
              <div className="cc-provider-right"><StatePill state={state} /><span className="cc-provider-time">{relativeDate(provider.last_run_at)}</span>{task && <Tooltip title={`Run ${provider.label} task`}><span><IconButton size="small" aria-label={`Run ${provider.label}`} disabled={demoMode || !!pendingAction || jobsError} onClick={() => runJob(task)}><PlayArrow fontSize="small" /></IconButton></span></Tooltip>}</div>
            </div>;
          })}</div>
        </Panel>
      </Grid>
      <Grid item xs={12} lg={7}>
        <Panel eyebrow="ORGANIC DISCOVERY" title="High-impression search gaps" action={<Button component={Link} to="/admin/manage/analytics" className="cc-text-button" endIcon={<ArrowOutward />}>Analytics</Button>}>
          {gaps.length ? <div className="cc-table-scroll"><table className="cc-table cc-gap-table"><thead><tr><th>Search query</th><th>Clicks</th><th>Impressions</th><th>CTR</th></tr></thead><tbody>
            {gaps.map((gap, index) => <tr key={`${gap.query}-${index}`}><td><div className="cc-query"><QueryStats fontSize="small" /><b>{gap.query}</b></div></td><td>{formatNum(gap.clicks)}</td><td>{formatNum(gap.impressions)}</td><td><span className="cc-ctr">{(Number(gap.ctr || 0) * 100).toFixed(2)}%</span></td></tr>)}
          </tbody></table></div> : <div className="cc-discovery-empty"><div className="cc-discovery-icon"><QueryStats /></div><div><b>{!data ? 'Search query data unavailable' : data.providers?.search_console?.state === 'unconfigured' ? 'Search Console is not connected' : 'No query gaps reported'}</b><p>{!data ? 'No query suggestions are shown until a live Search Console snapshot is available.' : data.providers?.search_console?.state === 'unconfigured' ? 'Connect a Search Console task to see actual high-impression queries with low click-through.' : 'Search suggestions are based on returned search queries only. None are available in this snapshot.'}</p></div></div>}
        </Panel>
      </Grid>
    </Grid>

    <Panel eyebrow="TASK HISTORY" title="Recent sync activity" action={<span className="cc-panel-meta">{runsError ? 'HISTORY UNAVAILABLE' : `${runs.length} RECENT RUN${runs.length === 1 ? '' : 'S'}`}</span>}>
      {runs.length ? <div className="cc-activity-list">{runs.slice(0, 8).map((run, index) => {
        const state = String(run.status || '').toLowerCase();
        const failed = state === 'failed';
        const result = typeof run.result === 'string' ? run.result : run.result ? JSON.stringify(run.result) : null;
        return <div className="cc-activity-row" key={run.id || `${run.mode}-${index}`}>
          <span className={`cc-activity-mark ${failed ? 'is-failed' : state === 'completed' ? 'is-complete' : ''}`}>{failed ? <ErrorOutline /> : state === 'completed' ? <CheckCircleOutline /> : <Autorenew />}</span>
          <div className="cc-activity-main"><div><b>{MODES[run.mode] || run.mode || 'Sync task'}</b><StatePill state={state} /></div><small>{result || run.error_summary || (run.status === 'QUEUED' ? 'Waiting for a worker' : 'No run details returned')}</small></div>
          <div className="cc-activity-counts"><span>{formatNum(run.updated_count)} updated</span>{Number(run.failed_count) > 0 && <span className="cc-failed-count">{formatNum(run.failed_count)} failed</span>}</div>
          <time>{dateTime(run.created_at || run.scheduled_at)}</time>
        </div>;
      })}</div> : <EmptyPanel>{runsError ? 'Run history is unavailable.' : 'No sync runs have been recorded yet.'}</EmptyPanel>}
    </Panel>

    <Dialog open={jobDialogOpen} onClose={closeJobDialog} className="cc-dialog" fullWidth maxWidth="sm">
      <DialogTitle>Create a sync task</DialogTitle>
      <DialogContent>
        <DialogContentText sx={{ mb: 2 }}>Configure an authenticated scheduled job. New tasks run only through the backend worker.</DialogContentText>
        <Stack spacing={1.5}>
          <TextField select label="Task type" value={draft.mode} onChange={(event) => setDraft({ ...draft, mode: event.target.value })}>
            {Object.entries(MODES).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}
          </TextField>
          {['IMPORT', 'PRICE'].includes(draft.mode) && <TextField label="Import source ID" type="number" value={draft.source} onChange={(event) => setDraft({ ...draft, source: event.target.value })} helperText="Find source IDs in Product Import." />}
          {draft.mode === 'IMPORT' && <>
            <TextField label="Source category path" value={draft.category_path} onChange={(event) => setDraft({ ...draft, category_path: event.target.value })} placeholder="Women / Knitwear" />
            <TextField label="Target category ID" type="number" value={draft.target_category} onChange={(event) => setDraft({ ...draft, target_category: event.target.value })} />
          </>}
          <TextField select label="Schedule" value={draft.interval_minutes} onChange={(event) => setDraft({ ...draft, interval_minutes: event.target.value })}>
            {INTERVALS.map((option) => <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>)}
          </TextField>
          <TextField label="Batch limit" type="number" inputProps={{ min: 1, max: 12, step: 1 }} value={draft.batch_limit} onChange={(event) => setDraft({ ...draft, batch_limit: event.target.value })} />
        </Stack>
        {draftError && <Alert severity="error" sx={{ mt: 1.5 }}>{draftError}</Alert>}
        {actionError && <Alert severity="error" sx={{ mt: 1.5 }}>{actionError.message}</Alert>}
      </DialogContent>
      <DialogActions>
        <Button disabled={!!pendingAction} onClick={closeJobDialog}>Cancel</Button>
        <Button variant="contained" disabled={!!pendingAction} onClick={createJob}>{pendingAction === 'create' ? 'Creating…' : 'Create task'}</Button>
      </DialogActions>
    </Dialog>

    <footer className="cc-footer"><span><span className="cc-footer-dot" /> {demoMode ? 'DEMO SNAPSHOT' : error ? 'LIVE SOURCE DISCONNECTED' : 'LIVE SOURCE CHECKED'} · {demoMode ? 'No server connection' : lastUpdatedAt ? dateTime(lastUpdatedAt) : 'Waiting for first response'}</span><span>Fabrything · Shop operations</span></footer>
  </div>;
}
