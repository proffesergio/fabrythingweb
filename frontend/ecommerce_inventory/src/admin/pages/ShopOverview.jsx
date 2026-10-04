import React from 'react';
import { Alert, Box, Button, Chip, Container, Grid, Typography } from '@mui/material';
import { Link } from 'react-router-dom';
import useOverview from './useOverview';
import { MODULES } from '../modules/registry';
import { AlertRow, fmtBDT, fmtNum, KpiCard, RecentTable, TopItems, TrendPanel, WidgetState } from '../widgets';

const META = MODULES.shop;

export default function ShopOverview() {
  const { data, loading, failed, retry, days, setDays } = useOverview(META.overviewApi, 'ov_shop');
  const k = data?.kpis || {};
  const alerts = data?.alerts || {};
  const showState = !data && (loading || failed);

  return (
    <Container maxWidth="xl" sx={{ py: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2, flexWrap: 'wrap' }}>
        <Typography variant="h5" fontWeight={900}>Shop Overview</Typography>
        <Chip size="small" label={META.label} sx={{ bgcolor: `${META.color}1e`, color: META.color, fontWeight: 800 }} />
        <Box sx={{ flex: 1 }} />
        <Button size="small" component={Link} to="/admin/manage/salesorder" variant="outlined">Orders</Button>
        <Button size="small" component={Link} to="/admin/manage/product" variant="outlined">Products</Button>
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
            <Grid item xs={6} md={3}><KpiCard label="Revenue (7d)" value={fmtBDT(k.revenue_7d)} delta={k.revenue_delta} spark={data?.series} color={META.color} /></Grid>
            <Grid item xs={6} md={3}><KpiCard label="Orders (7d)" value={fmtNum(k.orders_7d)} delta={k.orders_delta} spark={(data?.series || []).map((p) => ({ v: p.count }))} color="#1976d2" /></Grid>
            <Grid item xs={6} md={3}><KpiCard label="Avg order value" value={fmtBDT(k.avg_order_value)} color="#6A1B9A" /></Grid>
            <Grid item xs={6} md={3}><KpiCard label="Pending verification" value={fmtNum(k.pending_verification)} color="#EF6C00" /></Grid>
          </Grid>

          {(alerts.pending_orders > 0 || alerts.low_stock > 0) && (
            <Box sx={{ mb: 2 }}>
              {alerts.pending_orders > 0 && (
                <AlertRow to="/admin/manage/salesorder" actionLabel="Review orders">
                  <strong>{alerts.pending_orders}</strong> order(s) waiting for verification.
                </AlertRow>
              )}
              {alerts.low_stock > 0 && (
                <AlertRow severity={alerts.out_of_stock > 0 ? 'error' : 'warning'} to="/admin/manage/product" actionLabel="Check stock">
                  <strong>{alerts.low_stock}</strong> variant(s) low on stock
                  {alerts.out_of_stock > 0 && <> ({alerts.out_of_stock} out of stock)</>}.
                </AlertRow>
              )}
            </Box>
          )}

          <Grid container spacing={2}>
            <Grid item xs={12} md={8}>
              <TrendPanel
                title="Revenue overview" subtitle="COD orders, canceled/returned excluded"
                data={data?.series} range={days} onRange={setDays} color={META.color} formatY={fmtBDT}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TopItems
                title="Top products"
                items={(data?.top_products || []).map((p) => ({
                  name: p.name, sub: `${fmtNum(p.qty)} sold`, display: fmtBDT(p.revenue), value: p.qty,
                }))}
              />
            </Grid>
            <Grid item xs={12}>
              <RecentTable
                title="Recent orders"
                viewAllTo="/admin/manage/salesorder"
                columns={[
                  { key: 'order_number', flex: 1.2 },
                  { key: 'contact_name', flex: 1 },
                  {
                    key: 'status', flex: 1,
                    render: (r) => <Chip size="small" label={r.status} color={r.status === 'DELIVERED' ? 'success' : r.status === 'CANCELED' ? 'error' : 'default'} />,
                  },
                  { key: 'total_amount', flex: 0.8, align: 'right', render: (r) => <strong>{fmtBDT(r.total_amount)}</strong> },
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
