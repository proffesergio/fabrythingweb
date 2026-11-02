import { useEffect, useState, useCallback } from 'react';
import { Box, Typography, Card, Stack, Chip, Button, CircularProgress } from '@mui/material';
import useApi from '../hooks/APIHandler';

// Next legal statuses per FoodOrder.ALLOWED_TRANSITIONS (backend enforces authoritatively).
const NEXT = {
  PLACED: [['CONFIRMED', 'Confirm'], ['CANCELLED', 'Cancel']],
  CONFIRMED: [['PREPARING', 'Start preparing'], ['CANCELLED', 'Cancel']],
  PREPARING: [['OUT_FOR_DELIVERY', 'Send out'], ['CANCELLED', 'Cancel']],
  OUT_FOR_DELIVERY: [['DELIVERED', 'Mark delivered']],
  DELIVERED: [],
  CANCELLED: [],
};

export default function VendorOrders() {
  const { callApi, loading } = useApi();
  const [orders, setOrders] = useState([]);

  const fetchOrders = useCallback(async () => {
    const res = await callApi({ url: 'food/vendor/orders/', method: 'GET' });
    setOrders(res?.data?.data || []);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { fetchOrders(); }, [fetchOrders]);

  const advance = async (id, status) => {
    const res = await callApi({ url: `food/vendor/orders/${id}/status/`, method: 'PATCH', body: { status } });
    if (res?.status === 200) fetchOrders();
  };

  if (loading && !orders.length) return <Box sx={{ textAlign: 'center', py: 8 }}><CircularProgress /></Box>;

  return (
    <Box sx={{ p: 2, maxWidth: 800, mx: 'auto' }}>
      <Typography variant="h5" sx={{ mb: 2 }}>Incoming orders</Typography>
      {orders.length === 0 && <Typography color="text.secondary">No orders yet.</Typography>}
      {orders.map((o) => (
        <Card key={o.id} sx={{ p: 2, mb: 1 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Box>
              <Typography fontWeight={700}>{o.order_code}</Typography>
              <Typography variant="body2" color="text.secondary">
                {o.guest_name} · ৳{o.total} · {o.items.length} items
              </Typography>
            </Box>
            <Chip label={o.status} size="small" />
          </Stack>
          <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: 'wrap', gap: 1 }}>
            {(NEXT[o.status] || []).map(([status, label]) => (
              <Button
                key={status}
                size="small"
                variant={status === 'CANCELLED' ? 'outlined' : 'contained'}
                color={status === 'CANCELLED' ? 'error' : 'primary'}
                onClick={() => advance(o.id, status)}
              >
                {label}
              </Button>
            ))}
          </Stack>
        </Card>
      ))}
    </Box>
  );
}
