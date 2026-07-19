import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Box, Typography, Card, Stack, Chip, CircularProgress } from '@mui/material';
import useApi from '../../hooks/APIHandler';

export default function FoodMyOrders() {
  const { callApi, loading } = useApi();
  const [orders, setOrders] = useState([]);

  useEffect(() => {
    (async () => {
      const res = await callApi({ url: 'food/orders/', method: 'GET' });
      setOrders(res?.data?.data || []);
    })();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) return <Box sx={{ textAlign: 'center', py: 8 }}><CircularProgress /></Box>;
  if (!orders.length) {
    return <Typography color="text.secondary" sx={{ py: 8, textAlign: 'center' }}>No food orders yet.</Typography>;
  }

  return (
    <Box sx={{ maxWidth: 640, mx: 'auto' }}>
      <Typography variant="h5" sx={{ mb: 2 }}>My food orders</Typography>
      {orders.map((o) => (
        <Card
          key={o.id}
          component={Link}
          to={`/food/order/${o.order_code}`}
          sx={{ p: 2, mb: 1, display: 'block', textDecoration: 'none' }}
        >
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Box>
              <Typography>{o.order_code} · {o.restaurant_name}</Typography>
              <Typography variant="body2" color="text.secondary">৳{o.total}</Typography>
            </Box>
            <Chip size="small" label={o.status} color={o.status === 'DELIVERED' ? 'success' : 'default'} />
          </Stack>
        </Card>
      ))}
    </Box>
  );
}
