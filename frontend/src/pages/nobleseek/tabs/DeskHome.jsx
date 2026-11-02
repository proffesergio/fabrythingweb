import React, { useCallback, useEffect, useState } from 'react';
import { Alert, Box, Button, Card, CardContent, Grid, Typography } from '@mui/material';
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import useApi from '../../../hooks/APIHandler';
import { readSnap, writeSnap } from '../../../admin/snap';
import { AlertRow, KpiCard, TopItems, TrendPanel, WidgetState } from '../../../admin/widgets';
import { fetchBreaking } from '../../../nobleseek/api';
import ShareMenu from '../ShareMenu';

const COLORS = ['#F2631F', '#1976d2', '#2E7D32', '#6A1B9A', '#EF6C00', '#00838F', '#C2185B', '#5D4037', '#455A64', '#7B1FA2', '#00695C', '#F9A825'];

function StatCard({ label, value, color, onMore }) {
  return (
    <Card sx={{ bgcolor: color, color: 'white', height: '100%' }}>
      <CardContent sx={{ pb: '8px !important' }}>
        <Typography variant="h4" fontWeight={900}>{value}</Typography>
        <Typography variant="body2" sx={{ opacity: 0.92 }}>{label}</Typography>
        <Box sx={{ borderTop: '1px solid rgba(255,255,255,0.35)', mt: 1, pt: 0.5, textAlign: 'center' }}>
          <Button size="small" onClick={onMore} sx={{ color: 'white', fontWeight: 700 }}>আরও →</Button>
        </Box>
      </CardContent>
    </Card>
  );
}

// Dashboard home: stat cards with drills, category pie, activity, pipeline,
// featured lineup, top stories with sharing — the reference layout, Bangla.
export default function DeskHome({ cats, onShowArticles, onShowTab }) {
  const { callApi } = useApi();
  const [ov, setOv] = useState(() => readSnap('ns_nsoverview'));
  const [breaking, setBreaking] = useState([]);
  const [tagsCount, setTagsCount] = useState(null);
  const [loading, setLoading] = useState(!ov);
  const [failed, setFailed] = useState(false);
  const [days, setDays] = useState(14);

  const load = useCallback(async (d = 14) => {
    setLoading(true);
    setFailed(false);
    const [o, t] = await Promise.all([
      callApi({ url: `store/nobleseek/admin/overview/?days=${d}`, silent: true, timeout: 25000 }),
      callApi({ url: 'store/nobleseek/admin/tags/', silent: true, timeout: 25000 }),
    ]);
    const payload = o?.status === 200 ? (o.data?.data ?? o.data) : null;
    if (payload) { setOv(payload); writeSnap('ns_nsoverview', payload); }
    else setFailed(true);
    if (t?.status === 200) setTagsCount((t.data?.data ?? t.data ?? []).length);
    fetchBreaking(6).then(setBreaking).catch(() => {});
    setLoading(false);
  }, [callApi]);

  useEffect(() => { load(days); }, [load, days]);

  const k = ov?.kpis || {};
  const alerts = ov?.alerts || {};
  const pie = (cats || []).filter((c) => (c.article_count || 0) > 0)
    .map((c) => ({ name: c.name, value: c.article_count }));

  if (!ov && (loading || failed)) {
    return <WidgetState loading={loading} error={failed} onRetry={() => load(days)} height={320} />;
  }

  const cards = [
    { label: 'প্রকাশিত', value: k.published ?? '—', color: '#2E7D32', drill: () => onShowArticles({ status: 'PUBLISHED' }) },
    { label: 'ব্রেকিং', value: breaking.length || (k.breaking ?? '—'), color: '#C62828', drill: () => onShowArticles({ breaking: true }) },
    { label: 'বিভাগ', value: cats?.length ?? '—', color: '#00838F', drill: () => onShowTab('categories') },
    { label: 'ট্যাগ', value: tagsCount ?? '—', color: '#F9A825', drill: () => onShowTab('tags') },
    { label: 'মোট পঠিত', value: k.total_views ?? '—', color: '#6A1B9A', drill: () => onShowArticles({}) },
    { label: 'ট্রেন্ড ইনবক্স', value: k.trends_new ?? '—', color: '#EF6C00', drill: () => onShowTab('trends') },
    { label: 'রিভিউ সারি', value: k.review ?? '—', color: '#C2185B', drill: () => onShowArticles({ status: 'REVIEW' }) },
    { label: 'টিম', value: k.staff ?? '—', color: '#455A64', drill: () => onShowTab('ads') },
  ];

  return (
    <Box>
      {failed && (
        <Alert severity="warning" sx={{ mb: 2 }} action={<Button size="small" onClick={() => load(days)}>পুনরায়</Button>}>
          শেষ সংরক্ষিত তথ্য দেখানো হচ্ছে।
        </Alert>
      )}
      <Grid container spacing={2} sx={{ mb: 2 }}>
        {cards.map((c) => (
          <Grid item xs={6} sm={4} md={3} key={c.label}>
            <StatCard {...c} onMore={c.drill} />
          </Grid>
        ))}
      </Grid>

      {/* Publishing pipeline */}
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={6} md={3}><KpiCard label="খসড়া" value={k.drafts ?? '—'} color="#78909C" /></Grid>
        <Grid item xs={6} md={3}><KpiCard label="রিভিউতে" value={k.review ?? '—'} color="#EF6C00" /></Grid>
        <Grid item xs={6} md={3}><KpiCard label="শিডিউলড" value={alerts.scheduled ?? '—'} color="#1976d2" /></Grid>
        <Grid item xs={6} md={3}><KpiCard label="মন্তব্য অপেক্ষমাণ" value={alerts.pending_comments ?? '—'} color="#6A1B9A" /></Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <Card variant="outlined" sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="subtitle1" fontWeight={800} gutterBottom>বিভাগ অনুযায়ী খবর</Typography>
              {pie.length ? (
                <Box sx={{ height: 280 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={pie} dataKey="value" nameKey="name" outerRadius={95} label={({ percent }) => `${(percent * 100).toFixed(0)}%`}>
                        {pie.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                      </Pie>
                      <Tooltip />
                      <Legend layout="vertical" align="right" verticalAlign="middle" />
                    </PieChart>
                  </ResponsiveContainer>
                </Box>
              ) : (
                <Typography variant="body2" color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>এখনো বিভাগভিত্তিক খবর নেই।</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <TrendPanel
            title="প্রকাশনা কার্যক্রম" subtitle="প্রতিদিন প্রকাশিত প্রতিবেদন"
            data={ov?.series} dataKey="count" range={days}
            onRange={(d) => { setDays(d); load(d); }} color="#F2631F"
          />
        </Grid>
        <Grid item xs={12} md={6}>
          <TopItems
            title="সর্বাধিক পঠিত"
            items={(ov?.top_stories || []).slice(0, 5).map((a) => ({
              name: a.headline, sub: a.published_at ? new Date(a.published_at).toLocaleDateString('bn-BD') : '',
              display: Number(a.view_count || 0).toLocaleString('en-US'), value: a.view_count || 0,
            }))}
          />
          {(ov?.top_stories || []).length > 0 && (
            <Box sx={{ mt: 1 }}>
              <Typography variant="caption" color="text.secondary">শেয়ার করুন:</Typography>
              {(ov?.top_stories || []).slice(0, 3).map((a) => (
                <Box key={a.slug} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <Typography variant="caption" sx={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {a.headline}
                  </Typography>
                  <ShareMenu article={a} />
                </Box>
              ))}
            </Box>
          )}
        </Grid>
        <Grid item xs={12} md={6}>
          <Card variant="outlined" sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="subtitle1" fontWeight={800} gutterBottom>ফিচার্ড লাইনআপ</Typography>
              <Typography variant="caption" color="text.secondary">লিড: {(ov?.top_stories || [])[0]?.headline || '—'}</Typography>
              <Typography variant="subtitle2" fontWeight={800} sx={{ mt: 1.5, mb: 0.5 }}>ব্রেকিং টিকার ({breaking.length})</Typography>
              {breaking.map((b) => (
                <Typography key={b.id || b.slug} variant="body2" sx={{ py: 0.5, borderBottom: '1px solid #f0f0f0' }}>
                  • {b.headline_bn || b.headline}
                </Typography>
              ))}
              {!breaking.length && (
                <Typography variant="body2" color="text.secondary">কোনো ব্রেকিং নেই — প্রতিবেদনে Breaking ফ্ল্যাগ দিন।</Typography>
              )}
              {(alerts.empty_sections || []).length > 0 && (
                <Box sx={{ mt: 1.5 }}>
                  <AlertRow severity="info">খালি বিভাগ: {alerts.empty_sections.join(', ')}</AlertRow>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
