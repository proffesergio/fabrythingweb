import React from 'react';
import { Alert, Box, Button, Chip, Container, Grid, Typography } from '@mui/material';
import { Link } from 'react-router-dom';
import useOverview from './useOverview';
import { MODULES } from '../modules/registry';
import { AlertRow, fmtBDT, fmtNum, KpiCard, RecentTable, TopItems, TrendPanel, WidgetState } from '../widgets';

const META = MODULES.print;

export default function PrintOverview() {
  const { data, loading, failed, retry, days, setDays } = useOverview(META.overviewApi, 'ov_print');
  const k = data?.kpis || {};
  const alerts = data?.alerts || {};
  const showState = !data && (loading || failed);

  return (
    <Container maxWidth="xl" sx={{ py: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2, flexWrap: 'wrap' }}>
        <Typography variant="h5" fontWeight={900}>Printing Press Overview</Typography>
        <Chip size="small" label={META.label} sx={{ bgcolor: `${META.color}1e`, color: META.color, fontWeight: 800 }} />
        <Box sx={{ flex: 1 }} />
        <Button size="small" component={Link} to="/admin/manage/print/press-orders" variant="outlined">Press Orders</Button>
        <Button size="small" component={Link} to="/admin/manage/print/catalog" variant="outlined">Catalog</Button>
        <Button size="small" component={Link} to="/admin/manage/print/showcase" variant="outlined">Showcase</Button>
        <Button size="small" component={Link} to="/admin/manage/print/corporate" variant="outlined">Corporate</Button>
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
            <Grid item xs={6} md={3}><KpiCard label="Press orders (7d)" value={fmtNum(k.orders_7d)} delta={k.orders_delta} spark={(data?.series || []).map((p) => ({ v: p.count }))} color="#1976d2" /></Grid>
            <Grid item xs={6} md={3}><KpiCard label="Avg order value" value={fmtBDT(k.avg_order_value)} color="#00796B" /></Grid>
            <Grid item xs={6} md={3}><KpiCard label="Artwork review queue" value={fmtNum(k.artwork_review)} color="#EF6C00" /></Grid>
          </Grid>

          <Box sx={{ mb: 2 }}>
            {alerts.pending_payment > 0 && (
              <AlertRow to="/admin/manage/print/press-orders" actionLabel="Press orders">
                <strong>{alerts.pending_payment}</strong> press order(s) waiting for payment.
              </AlertRow>
            )}
            {alerts.artwork_review > 0 && (
              <AlertRow severity="info" to="/admin/manage/print/press-orders" actionLabel="Review artwork">
                <strong>{alerts.artwork_review}</strong> order(s) waiting for artwork review.
              </AlertRow>
            )}
            {alerts.failed_payments > 0 && (
              <AlertRow severity="error" to="/admin/manage/print/press-orders" actionLabel="Failed payments">
                <strong>{alerts.failed_payments}</strong> order(s) with failed payments need follow-up.
              </AlertRow>
            )}
            {alerts.open_quotations > 0 && (
              <AlertRow severity="info" to="/admin/manage/print/corporate" actionLabel="Quotations">
                <strong>{alerts.open_quotations}</strong> open quotation(s) awaiting decision.
              </AlertRow>
            )}
          </Box>

          <Grid container spacing={2}>
            <Grid item xs={12} md={8}>
              <TrendPanel
                title="Press revenue" subtitle="Canceled orders excluded"
                data={data?.series} range={days} onRange={setDays} color={META.color} formatY={fmtBDT}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TopItems
                title="Top press products"
                items={(data?.top_products || []).map((p) => ({
                  name: p.name, sub: `${fmtNum(p.qty)} orders`, display: fmtBDT(p.revenue), value: p.qty,
                }))}
              />
            </Grid>
            <Grid item xs={12}>
              <RecentTable
                title="Recent press orders"
                viewAllTo="/admin/manage/print/press-orders"
                columns={[
                  { key: 'id', flex: 0.5, render: (r) => <Typography variant="body2">#{r.id}</Typography> },
                  { key: 'product', flex: 1.2 },
                  { key: 'customer', flex: 1 },
                  {
                    key: 'status', flex: 1,
                    render: (r) => <Chip size="small" label={String(r.status || '').replace(/_/g, ' ')} color={r.status === 'DELIVERED' ? 'success' : r.status === 'CANCELLED' ? 'error' : 'default'} />,
                  },
                  { key: 'total', flex: 0.8, align: 'right', render: (r) => <strong>{fmtBDT(r.total)}</strong> },
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
