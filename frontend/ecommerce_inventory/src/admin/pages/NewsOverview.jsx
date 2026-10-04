import React from 'react';
import { Alert, Box, Button, Chip, Container, Grid, Typography } from '@mui/material';
import { Link } from 'react-router-dom';
import useOverview from './useOverview';
import { MODULES } from '../modules/registry';
import { toBn } from '../../nobleseek/bn';
import { AlertRow, fmtNum, KpiCard, TopItems, TrendPanel, WidgetState } from '../widgets';

const META = MODULES.news;
const bn = (n) => toBn(Number(n || 0).toLocaleString('en-US'));

// Bangla-first desk overview inside the English admin shell: labels in
// Bangla, drill links into the NobleSeek desk tabs.
export default function NewsOverview() {
  const { data, loading, failed, retry, days, setDays } = useOverview(META.overviewApi, 'ov_news');
  const k = data?.kpis || {};
  const alerts = data?.alerts || {};
  const showState = !data && (loading || failed);

  return (
    <Container maxWidth="xl" sx={{ py: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2, flexWrap: 'wrap' }}>
        <Typography variant="h5" fontWeight={900}>নোবেলসিক ওভারভিউ</Typography>
        <Chip size="small" label={META.label} sx={{ bgcolor: `${META.color}1e`, color: META.color, fontWeight: 800 }} />
        <Box sx={{ flex: 1 }} />
        <Button size="small" component={Link} to="/admin/manage/nobleseek" variant="contained">ডেস্ক খুলুন</Button>
      </Box>

      {showState ? (
        <WidgetState loading={loading} error={failed} onRetry={retry} height={320} />
      ) : (
        <>
          {failed && (
            <Alert severity="warning" sx={{ mb: 2 }} action={<Button size="small" onClick={retry}>পুনরায় চেষ্টা</Button>}>
              শেষ সংরক্ষিত তথ্য দেখানো হচ্ছে — সার্ভার জেগে উঠতে পারে।
            </Alert>
          )}
          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid item xs={6} md={3}><KpiCard label="প্রকাশিত" value={bn(k.published)} spark={(data?.series || []).map((p) => ({ v: p.count }))} color={META.color} /></Grid>
            <Grid item xs={6} md={3}><KpiCard label="খসড়া" value={bn(k.drafts)} color="#1976d2" /></Grid>
            <Grid item xs={6} md={3}><KpiCard label="রিভিউতে" value={bn(k.review)} color="#EF6C00" /></Grid>
            <Grid item xs={6} md={3}><KpiCard label="মোট পঠিত" value={bn(k.total_views)} color="#6A1B9A" /></Grid>
          </Grid>

          <Box sx={{ mb: 2 }}>
            {alerts.review_queue > 0 && (
              <AlertRow to="/admin/manage/nobleseek" actionLabel="ডেস্ক">
                <strong>{bn(alerts.review_queue)}</strong>টি প্রতিবেদন রিভিউয়ের অপেক্ষায়।
              </AlertRow>
            )}
            {alerts.trends_new > 0 && (
              <AlertRow severity="info" to="/admin/manage/nobleseek" actionLabel="ইনবক্স">
                ট্রেন্ড ইনবক্সে <strong>{bn(alerts.trends_new)}</strong>টি নতুন কীওয়ার্ড।
              </AlertRow>
            )}
            {(alerts.empty_sections || []).length > 0 && (
              <AlertRow severity="info">
                খালি বিভাগ: {alerts.empty_sections.join(', ')} — প্রথম প্রতিবেদন প্রকাশ করুন।
              </AlertRow>
            )}
          </Box>

          <Grid container spacing={2}>
            <Grid item xs={12} md={8}>
              <TrendPanel
                title="প্রকাশনা কার্যক্রম" subtitle="প্রতিদিন প্রকাশিত প্রতিবেদন"
                data={data?.series} dataKey="count" range={days} onRange={setDays} color={META.color}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TopItems
                title="সর্বাধিক পঠিত"
                items={(data?.top_stories || []).map((a) => ({
                  name: a.headline, sub: a.published_at ? new Date(a.published_at).toLocaleDateString('bn-BD') : '',
                  display: bn(a.view_count), value: a.view_count,
                }))}
              />
            </Grid>
          </Grid>
        </>
      )}
    </Container>
  );
}
