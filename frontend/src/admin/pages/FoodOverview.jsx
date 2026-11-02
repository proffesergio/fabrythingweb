import React from 'react';
import { Alert, Box, Button, Chip, Container, Grid, Typography } from '@mui/material';
import { Link } from 'react-router-dom';
import useOverview from './useOverview';
import { MODULES } from '../modules/registry';
import { AlertRow, fmtBDT, fmtNum, KpiCard, RecentTable, TopItems, TrendPanel, WidgetState } from '../widgets';

const META = MODULES.food;

export default function FoodOverview() {
  const { data, loading, failed, retry, days, setDays } = useOverview(META.overviewApi, 'ov_food');
  const k = data?.kpis || {};
  const alerts = data?.alerts || {};
  const showState = !data && (loading || failed);

  return (
    <Container maxWidth="xl" sx={{ py: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2, flexWrap: 'wrap' }}>
        <Typography variant="h5" fontWeight={900}>Food Overview</Typography>
        <Chip size="small" label={META.label} sx={{ bgcolor: `${META.color}1e`, color: META.color, fontWeight: 800 }} />
        <Box sx={{ flex: 1 }} />
        <Button size="small" component={Link} to="/admin/manage/food/orders" variant="outlined">Orders</Button>
        <Button size="small" component={Link} to="/admin/manage/food/restaurants" variant="outlined">Restaurants</Button>
      </Box>

      {showState ? (
        <WidgetState loading={loading} error={failed} onRetry={retry} height={320} />
      ) : (
        <>
          {failed && (
            <Alert severity="warning" sx={{ mb: 2 }} action={<Button size="small" onClick={retry}>Retry</Button>}>
              Showing last saved snapshot — the server may be waking up.
            </Alert>
          )}
          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid item xs={6} md={3}><KpiCard label="GMV (7d)" value={fmtBDT(k.gmv_7d)} delta={k.gmv_delta} spark={data?.series} color={META.color} /></Grid>
            <Grid item xs={6} md={3}><KpiCard label="Orders (7d)" value={fmtNum(k.orders_7d)} delta={k.orders_delta} spark={(data?.series || []).map((p) => ({ v: p.count }))} color="#1976d2" /></Grid>
            <Grid item xs={6} md={3}><KpiCard label="Active restaurants" value={fmtNum(k.active_restaurants)} color="#6A1B9A" /></Grid>
            <Grid item xs={6} md={3}><KpiCard label="Riders online now" value={fmtNum(k.online_riders)} color="#EF6C00" /></Grid>
          </Grid>

          <Box sx={{ mb: 2 }}>
            {alerts.unconfirmed_orders > 0 && (
              <AlertRow to="/admin/manage/food/orders" actionLabel="Dispatch queue">
                <strong>{alerts.unconfirmed_orders}</strong> order(s) placed but not confirmed.
              </AlertRow>
            )}
            {alerts.pending_partners > 0 && (
              <AlertRow severity="info" to="/admin/manage/food/partners" actionLabel="Review partners">
                <strong>{alerts.pending_partners}</strong> restaurant application(s) awaiting approval.
              </AlertRow>
            )}
            {alerts.cash_to_collect > 0 && (
              <AlertRow severity="info" to="/admin/manage/food/rider-cash" actionLabel="Rider cash">
                <strong>{fmtBDT(alerts.cash_to_collect)}</strong> delivered but not yet collected.
              </AlertRow>
            )}
          </Box>

          <Grid container spacing={2}>
            <Grid item xs={12} md={8}>
              <TrendPanel
                title="Order volume" subtitle="GMV, canceled orders excluded"
                data={data?.series} range={days} onRange={setDays} color={META.color} formatY={fmtBDT}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TopItems
                title="Top restaurants"
                items={(data?.top_restaurants || []).map((r) => ({
                  name: r.name, sub: `${fmtNum(r.orders)} orders`, display: fmtBDT(r.gmv), value: r.orders,
                }))}
              />
            </Grid>
            <Grid item xs={12}>
              <RecentTable
                title="Recent orders"
                viewAllTo="/admin/manage/food/orders"
                columns={[
                  { key: 'code', flex: 0.8 },
                  { key: 'restaurant', flex: 1.2 },
                  {
                    key: 'status', flex: 1,
                    render: (r) => <Chip size="small" label={r.status} color={r.status === 'DELIVERED' ? 'success' : r.status === 'CANCELLED' ? 'error' : 'default'} />,
                  },
                  { key: 'total', flex: 0.7, align: 'right', render: (r) => <strong>{fmtBDT(r.total)}</strong> },
                  { key: 'created_at', flex: 1, render: (r) => <Typography variant="caption">{r.created_at ? new Date(r.created_at).toLocaleString() : '—'}</Typography> },
                ]}
                rows={data?.recent_orders}
              />
            </Grid>
          </Grid>
        </>
      )}
    </Container>
  );
}
