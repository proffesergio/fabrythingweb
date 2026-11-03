import React, { lazy, Suspense, useMemo, useState } from 'react';
import { Alert, Box, Button, CircularProgress, Tab, Tabs, TextField, Typography } from '@mui/material';
import { ArrowOutward } from '@mui/icons-material';
import { Link, useSearchParams } from 'react-router-dom';
import { useSelector } from 'react-redux';
import { ThemeProvider } from '@mui/material/styles';
import { controlCenterTheme } from '../theme';
import { MODULES, splitItems } from '../modules/registry';
import { toAdminPath } from '../../layout/sidebarNav';
import './ShopControlCenter.css';
const EMPTY_ITEMS = [];


const ShopOverview = lazy(() => import('./ShopOverview'));
const FoodOverview = lazy(() => import('./FoodOverview'));
const PrintOverview = lazy(() => import('./PrintOverview'));
const NewsOverview = lazy(() => import('./NewsOverview'));
const ShopControlCenter = lazy(() => import('./ShopControlCenter'));
const LegacyDashboard = lazy(() => import('../../pages/Home'));
const OVERVIEWS = { shop: ShopOverview, food: FoodOverview, print: PrintOverview, news: NewsOverview };

// Only expose tools returned by the permission-filtered menu API. Do not
// maintain a second, unrestricted catalog of management actions here.
export function toolGroups(items, module) {
  const { mine, shared } = splitItems(items, module);
  const flatten = (rows, trail = []) => rows.flatMap((item) => {
    const children = item.submenus || [];
    if (children.length) return flatten(children, [...trail, item.module_name]);
    const to = toAdminPath(item.module_url);
    if (!to || to === '/admin/home' || Object.values(MODULES).some((meta) => to === meta.home)
        || to === '/admin/shop/control-center') return [];
    return [{ label: item.module_name, to, group: trail.join(' / ') || 'Management' }];
  });
  const unique = (rows) => [...new Map(rows.map((row) => [row.to, row])).values()];
  return { module: unique(flatten(mine)), shared: unique(flatten(shared)) };
}

export default function ModuleControlCenter({ module }) {
  const meta = MODULES[module];
  const items = useSelector((state) => state.sidebardata?.items) || EMPTY_ITEMS;
  const status = useSelector((state) => state.sidebardata?.status);
  const [params, setParams] = useSearchParams();
  const [query, setQuery] = useState('');
  const groups = useMemo(() => toolGroups(items, module), [items, module]);
  const requestedTab = params.get('tab');
  const tab = requestedTab === 'tools' || (module === 'shop' && ['automation', 'business'].includes(requestedTab))
    ? requestedTab : 'operations';
  const Overview = OVERVIEWS[module];
  const changeTab = (_, value) => {
    setParams((previous) => { const next = new URLSearchParams(previous); next.set('tab', value); return next; });
  };
  const renderTools = (rows, title) => {
    const shown = rows.filter((row) => `${row.label} ${row.group}`.toLowerCase().includes(query.toLowerCase().trim()));
    if (!shown.length) return null;
    return <section className="cc-tool-section" aria-label={title}>
      <Typography component="h2" className="cc-panel-title">{title}</Typography>
      <div className="cc-tool-grid">{shown.map((tool) => <Button key={tool.to} component={Link} to={tool.to}
        className="cc-tool-link" endIcon={<ArrowOutward />}>
        <span><small>{tool.group}</small><strong>{tool.label}</strong></span>
      </Button>)}</div>
    </section>;
  };

  return <ThemeProvider theme={controlCenterTheme}><div className="cc-root cc-module-center">
    <header className="cc-header">
      <div className="cc-heading">
        <div className="cc-breadcrumb">FABRYTHING / {meta.short.toUpperCase()} / <b>CONTROL CENTER</b></div>
        <Typography component="h1" className="cc-title">{meta.short} Control Center</Typography>
        <p className="cc-subtitle">{meta.label} · operations, reporting and management</p>
      </div>
      <Button component={Link} to="?tab=tools" className="cc-overview-link">All management tools <ArrowOutward fontSize="small" /></Button>
    </header>
    <Tabs value={tab} onChange={changeTab} variant="scrollable" scrollButtons="auto" aria-label={`${meta.short} Control Center sections`} sx={{ mb: 3, borderBottom: '1px solid', borderColor: 'divider' }}>
      <Tab label="Operations" value="operations" />
      {module === 'shop' && <Tab label="Automation & insights" value="automation" />}
      {module === 'shop' && <Tab label="Business report" value="business" />}
      <Tab label="Management tools" value="tools" />
    </Tabs>
    <Box role="tabpanel" aria-label={`${meta.short} ${tab}`}>
      <Suspense fallback={<Box sx={{ p: 4, textAlign: 'center' }}><CircularProgress aria-label="Loading section" /></Box>}>
        {tab === 'operations' && <Overview embedded />}
        {tab === 'automation' && <ShopControlCenter embedded />}
        {tab === 'business' && <LegacyDashboard />}
        {tab === 'tools' && <>
          <TextField fullWidth size="small" label="Find a management tool" value={query} onChange={(event) => setQuery(event.target.value)} sx={{ mb: 3 }} />
          {status === 'loading' && !items.length && <CircularProgress aria-label="Loading granted tools" />}
          {status === 'failed' && <Alert severity="warning">Menus could not be refreshed. Reload to check your granted tools.</Alert>}
          {renderTools(groups.module, `${meta.short} tools`)}
          {renderTools(groups.shared, 'Shared administration')}
          {status !== 'loading' && ![...groups.module, ...groups.shared].some((row) => `${row.label} ${row.group}`.toLowerCase().includes(query.toLowerCase().trim())) &&
            <Alert severity="info">{query ? 'No tools match your search.' : 'No management tools have been granted to this account.'}</Alert>}
        </>}
      </Suspense>
    </Box>
  </div></ThemeProvider>;
}
