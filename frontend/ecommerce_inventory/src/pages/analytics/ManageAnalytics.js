import React, { useCallback, useEffect, useState } from 'react';
import {
    Box, Card, CardContent, Typography, Grid, Chip, Button, Tabs, Tab,
    Table, TableHead, TableBody, TableRow, TableCell, Switch, TextField,
    Link, Alert, FormControl, InputLabel, Select, MenuItem,
} from '@mui/material';
import {
    CheckCircle, Warning, OpenInNew, Refresh,
} from '@mui/icons-material';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import useApi from '../../hooks/APIHandler';

// Plugin-based traffic panel. Every provider (GA4, GTM, Meta Pixel, AdSense,
// internal log) renders from GET store/analytics/admin/overview/ — adding a
// backend provider plugin automatically adds a card here, no UI change needed.
// The internal event log is the fallback source of truth while GA4/AdSense
// are pending approval or blocked by ad-blockers.
const FUNNEL_LABELS = {
    page_view: 'Page views',
    view_item: 'Product views',
    add_to_cart: 'Add to carts',
    begin_checkout: 'Checkouts started',
    purchase: 'Purchases',
};

export default function ManageAnalytics() {
    const { callApi, loading } = useApi();
    const [tab, setTab] = useState(0);
    const [overview, setOverview] = useState(null);
    const [events, setEvents] = useState([]);
    const [eventFilter, setEventFilter] = useState('');
    const [providers, setProviders] = useState([]);
    const [editing, setEditing] = useState({});

    const fetchOverview = useCallback(async () => {
        const res = await callApi({ url: 'store/analytics/admin/overview/', silent: true });
        if (res?.data?.data) setOverview(res.data.data);
    }, [callApi]);

    const fetchProviders = useCallback(async () => {
        const res = await callApi({ url: 'store/analytics/admin/providers/', silent: true });
        if (res?.data?.data) setProviders(res.data.data);
    }, [callApi]);

    const fetchEvents = useCallback(async (event) => {
        const q = event ? `?event=${event}` : '';
        const res = await callApi({ url: `store/analytics/admin/events/${q}`, silent: true });
        if (res?.data?.results) setEvents(res.data.results);
        else if (Array.isArray(res?.data)) setEvents(res.data);
    }, [callApi]);

    useEffect(() => {
        fetchOverview();
        fetchProviders();
        fetchEvents('');
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const toggleProvider = async (key, isEnabled) => {
        await callApi({
            url: `store/analytics/admin/providers/${key}/`,
            method: 'PATCH', body: { is_enabled: !isEnabled }, silent: true,
        });
        fetchProviders();
        fetchOverview();
    };

    const saveProviderConfig = async (key) => {
        const cfg = editing[key];
        if (!cfg) return;
        // "measurement_id=G-XXX container_id=GTM-XXX" -> {measurement_id: ...}
        const parsed = {};
        cfg.split(/\s+/).forEach((pair) => {
            const [k, v] = pair.split('=');
            if (k && v) parsed[k.trim()] = v.trim();
        });
        await callApi({
            url: `store/analytics/admin/providers/${key}/`,
            method: 'PATCH', body: { config: parsed }, silent: true,
        });
        setEditing((e) => ({ ...e, [key]: '' }));
        fetchProviders();
        fetchOverview();
    };

    const byDay = (overview?.by_day || []).map((d) => ({
        day: String(d.day).slice(5),
        events: d.count,
    }));
    const funnel = overview?.funnel || [];
    const totals = overview?.totals || {};

    return (
        <Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Box>
                    <Typography variant="h5" fontWeight={700}>Traffic &amp; Analytics</Typography>
                    <Typography variant="body2" color="text.secondary">
                        Provider health, first-party funnel, and recent user activity
                    </Typography>
                </Box>
                <Button startIcon={<Refresh />} size="small" onClick={() => { fetchOverview(); fetchProviders(); fetchEvents(eventFilter); }}>
                    Refresh
                </Button>
            </Box>

            <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
                <Tab label="Overview" />
                <Tab label="Providers" />
                <Tab label="Recent events" />
            </Tabs>

            {tab === 0 && (
                <>
                    {!overview && (
                        <Typography color="text.secondary">{loading ? 'Loading…' : 'No data yet — visit the storefront, then refresh.'}</Typography>
                    )}
                    {overview && (
                        <>
                            <Grid container spacing={2} sx={{ mb: 2 }}>
                                {[
                                    { label: 'Events (7d)', value: totals.events_7d ?? 0 },
                                    { label: 'Sessions (7d)', value: totals.sessions_7d ?? 0 },
                                    { label: 'Purchases (7d)', value: totals.purchases_7d ?? 0 },
                                ].map((s) => (
                                    <Grid item xs={4} key={s.label}>
                                        <Card><CardContent>
                                            <Typography variant="body2" color="text.secondary">{s.label}</Typography>
                                            <Typography variant="h4" fontWeight={700}>{s.value}</Typography>
                                        </CardContent></Card>
                                    </Grid>
                                ))}
                            </Grid>

                            <Grid container spacing={2}>
                                <Grid item xs={12} md={7}>
                                    <Card sx={{ p: 2 }}>
                                        <Typography variant="h6" gutterBottom>Events per day (7d, internal log)</Typography>
                                        <Box sx={{ height: 250 }}>
                                            <ResponsiveContainer>
                                                <BarChart data={byDay}>
                                                    <CartesianGrid strokeDasharray="3 3" />
                                                    <XAxis dataKey="day" />
                                                    <YAxis allowDecimals={false} />
                                                    <Tooltip />
                                                    <Bar dataKey="events" fill="#2196F3" />
                                                </BarChart>
                                            </ResponsiveContainer>
                                        </Box>
                                    </Card>
                                </Grid>
                                <Grid item xs={12} md={5}>
                                    <Card sx={{ p: 2 }}>
                                        <Typography variant="h6" gutterBottom>Purchase funnel (7d)</Typography>
                                        {funnel.map((step) => {
                                            const [key, count] = Object.entries(step)[0];
                                            return (
                                                <Box key={key} sx={{ display: 'flex', justifyContent: 'space-between', py: 1, borderBottom: '1px solid', borderColor: 'divider' }}>
                                                    <Typography variant="body2">{FUNNEL_LABELS[key] || key}</Typography>
                                                    <Typography variant="body2" fontWeight={700}>{count}</Typography>
                                                </Box>
                                            );
                                        })}
                                        {funnel.length === 0 && (
                                            <Typography color="text.secondary">No funnel data yet.</Typography>
                                        )}
                                    </Card>
                                </Grid>
                            </Grid>

                            <Typography variant="h6" sx={{ mt: 3, mb: 1 }}>Provider health</Typography>
                            <Grid container spacing={2}>
                                {(overview.providers || []).map((p) => (
                                    <Grid item xs={12} md={6} key={p.key}>
                                        <Card sx={{ p: 2 }}>
                                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                                                {p.configured
                                                    ? <CheckCircle color="success" fontSize="small" />
                                                    : <Warning color="warning" fontSize="small" />}
                                                <Typography variant="subtitle1" fontWeight={700}>{p.name}</Typography>
                                                <Chip
                                                    label={p.is_enabled ? 'enabled' : 'disabled'}
                                                    size="small"
                                                    color={p.is_enabled ? 'success' : 'default'}
                                                />
                                            </Box>
                                            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>{p.detail}</Typography>
                                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>{p.docs_hint}</Typography>
                                            {p.setup_url && (
                                                <Link href={p.setup_url} target="_blank" rel="noreferrer" sx={{ fontSize: '0.8rem' }}>
                                                    Open console <OpenInNew sx={{ fontSize: 12 }} />
                                                </Link>
                                            )}
                                        </Card>
                                    </Grid>
                                ))}
                            </Grid>
                        </>
                    )}
                </>
            )}

            {tab === 1 && (
                <Card sx={{ p: 2 }}>
                    <Typography variant="h6" gutterBottom>Providers</Typography>
                    <Alert severity="info" sx={{ mb: 2 }}>
                        Browser tags live in <code>public/index.html</code> and Vercel env vars — this table is the
                        control plane (enable/disable + recorded IDs). Config format: <code>measurement_id=G-XXX</code>,{' '}
                        <code>container_id=GTM-XXX</code>, <code>pixel_id=123</code>, <code>publisher_id=ca-pub-XXX</code>.
                    </Alert>
                    {providers.map((p) => (
                        <Box key={p.key} sx={{ display: 'flex', gap: 2, alignItems: 'center', py: 1.5, borderBottom: '1px solid', borderColor: 'divider', flexWrap: 'wrap' }}>
                            <Box sx={{ minWidth: 200 }}>
                                <Typography variant="subtitle2" fontWeight={700}>{p.name}</Typography>
                                <Typography variant="caption" color="text.secondary">{p.key}</Typography>
                            </Box>
                            <Switch checked={!!p.is_enabled} onChange={() => toggleProvider(p.key, p.is_enabled)} />
                            <TextField
                                size="small" sx={{ flex: 1, minWidth: 240 }}
                                placeholder="key=value key=value…"
                                value={editing[p.key] ?? ''}
                                onChange={(e) => setEditing((ed) => ({ ...ed, [p.key]: e.target.value }))}
                            />
                            <Button size="small" variant="outlined" onClick={() => saveProviderConfig(p.key)}>Save</Button>
                        </Box>
                    ))}
                    {providers.length === 0 && <Typography color="text.secondary">Loading…</Typography>}
                </Card>
            )}

            {tab === 2 && (
                <Card sx={{ p: 2 }}>
                    <Box sx={{ display: 'flex', gap: 2, mb: 2, alignItems: 'center' }}>
                        <Typography variant="h6">Recent events</Typography>
                        <FormControl size="small" sx={{ minWidth: 180 }}>
                            <InputLabel>Filter</InputLabel>
                            <Select
                                value={eventFilter} label="Filter"
                                onChange={(e) => { setEventFilter(e.target.value); fetchEvents(e.target.value); }}
                            >
                                <MenuItem value="">All</MenuItem>
                                {Object.keys(FUNNEL_LABELS).concat(['search', 'signup', 'login']).map((ev) => (
                                    <MenuItem key={ev} value={ev}>{ev}</MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                    </Box>
                    <Table size="small">
                        <TableHead>
                            <TableRow>
                                <TableCell>Time</TableCell>
                                <TableCell>Event</TableCell>
                                <TableCell>Path</TableCell>
                                <TableCell>Session</TableCell>
                                <TableCell>User</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {events.map((e) => (
                                <TableRow key={e.id}>
                                    <TableCell>{e.created_at ? new Date(e.created_at).toLocaleString() : ''}</TableCell>
                                    <TableCell><Chip label={e.event} size="small" /></TableCell>
                                    <TableCell sx={{ maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis' }}>{e.path}</TableCell>
                                    <TableCell sx={{ maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis' }}>{e.session_id}</TableCell>
                                    <TableCell>{e.user_id ?? '—'}</TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                    {events.length === 0 && (
                        <Typography color="text.secondary" sx={{ py: 3, textAlign: 'center' }}>
                            No events yet. Browse the storefront (production host), then refresh.
                        </Typography>
                    )}
                </Card>
            )}
        </Box>
    );
}
