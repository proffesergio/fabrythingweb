import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Box, Typography, Card, Stack, Chip, CircularProgress, Button } from '@mui/material';
import ChevronRightRoundedIcon from '@mui/icons-material/ChevronRightRounded';
import { motion } from 'framer-motion';
import useApi from '../../hooks/APIHandler';

const STATUS_COLOR = {
  DELIVERED: 'success', CANCELLED: 'default', OUT_FOR_DELIVERY: 'primary',
  PREPARING: 'secondary', CONFIRMED: 'info', PLACED: 'warning',
};
const STATUS_LABEL = {
  PLACED: 'Placed', CONFIRMED: 'Confirmed', PREPARING: 'Preparing',
  OUT_FOR_DELIVERY: 'On the way', DELIVERED: 'Delivered', CANCELLED: 'Cancelled',
};

export default function FoodMyOrders() {
  const { callApi, loading } = useApi();
  const navigate = useNavigate();
  const [orders, setOrders] = useState([]);

  useEffect(() => {
    (async () => {
      const res = await callApi({ url: 'food/orders/', method: 'GET' });
      setOrders(res?.data?.data || []);
    })();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) return <Box sx={{ textAlign: 'center', py: 10 }}><CircularProgress color="primary" /></Box>;

  if (!orders.length) {
    return (
      <Box sx={{ textAlign: 'center', py: 10 }}>
        <Box sx={{ fontSize: 60, mb: 1 }}>🍽️</Box>
        <Typography variant="h6">No orders yet</Typography>
        <Typography color="text.secondary" sx={{ mb: 3 }}>Your food orders will show up here.</Typography>
        <Button variant="contained" onClick={() => navigate('/food')}>Find something to eat</Button>
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 640, mx: 'auto' }}>
      <Typography variant="h4" sx={{ mb: 2.5 }}>My orders</Typography>
      {orders.map((o, i) => (
        <Box key={o.id} component={motion.div} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: Math.min(i * 0.05, 0.3) }}>
          <Card component={Link} to={`/food/order/${o.order_code}`}
            sx={{ p: 2, mb: 1.5, display: 'block', textDecoration: 'none',
                  transition: 'transform .15s', '&:hover': { transform: 'translateX(3px)' } }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={1}>
              <Box sx={{ minWidth: 0 }}>
                <Typography sx={{ fontWeight: 800 }} noWrap>{o.restaurant_name}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {o.order_code} · ৳{o.total}
                  {o.created_at ? ` · ${new Date(o.created_at).toLocaleDateString()}` : ''}
                </Typography>
              </Box>
              <Stack direction="row" alignItems="center" spacing={0.5}>
                <Chip size="small" label={STATUS_LABEL[o.status] || o.status} color={STATUS_COLOR[o.status] || 'default'} sx={{ fontWeight: 700 }} />
                <ChevronRightRoundedIcon sx={{ color: 'text.secondary' }} />
              </Stack>
            </Stack>
          </Card>
        </Box>
      ))}
    </Box>
  );
}
