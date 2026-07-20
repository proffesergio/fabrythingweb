import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Box, Typography, Card, Divider, Stack, TextField, Button, CircularProgress } from '@mui/material';
import ReceiptLongRoundedIcon from '@mui/icons-material/ReceiptLongRounded';
import { motion } from 'framer-motion';
import useApi from '../../hooks/APIHandler';
import { FOOD } from '../theme';

const STEPS = ['PLACED', 'CONFIRMED', 'PREPARING', 'OUT_FOR_DELIVERY', 'DELIVERED'];
const LABELS = {
  PLACED: 'Placed', CONFIRMED: 'Confirmed', PREPARING: 'Preparing',
  OUT_FOR_DELIVERY: 'On the way', DELIVERED: 'Delivered',
};

function DeliveryTrack({ activeStep }) {
  const pct = activeStep <= 0 ? 0 : (activeStep / (STEPS.length - 1)) * 100;
  return (
    <Box sx={{ position: 'relative', mt: 5, mb: 1, px: 1 }}>
      {/* moving scooter */}
      <Box component={motion.div} aria-hidden
        animate={{ left: `${pct}%` }} transition={{ type: 'spring', stiffness: 120, damping: 18 }}
        sx={{ position: 'absolute', top: -34, transform: 'translateX(-50%)', fontSize: 26 }}>
        🛵
      </Box>
      {/* base + filled track */}
      <Box sx={{ position: 'relative', height: 6, borderRadius: 3, bgcolor: FOOD.line }}>
        <Box component={motion.div} animate={{ width: `${pct}%` }} transition={{ type: 'spring', stiffness: 120, damping: 18 }}
          sx={{ position: 'absolute', inset: 0, borderRadius: 3, background: `linear-gradient(90deg, ${FOOD.turmeric}, ${FOOD.primary})` }} />
        {STEPS.map((s, i) => {
          const done = i <= activeStep;
          const current = i === activeStep;
          return (
            <Box key={s} sx={{ position: 'absolute', top: '50%', left: `${(i / (STEPS.length - 1)) * 100}%`, transform: 'translate(-50%,-50%)' }}>
              <Box component={motion.div}
                animate={current ? { scale: [1, 1.25, 1] } : { scale: 1 }}
                transition={current ? { repeat: Infinity, duration: 1.4 } : {}}
                sx={{ width: 16, height: 16, borderRadius: '50%', border: `3px solid ${done ? FOOD.primary : FOOD.line}`,
                      bgcolor: done ? FOOD.primary : '#fff' }} />
            </Box>
          );
        })}
      </Box>
      <Stack direction="row" justifyContent="space-between" sx={{ mt: 1.5 }}>
        {STEPS.map((s, i) => (
          <Typography key={s} variant="caption" sx={{ width: 60, textAlign: 'center',
            fontWeight: i === activeStep ? 800 : 500, color: i <= activeStep ? 'text.primary' : 'text.secondary' }}>
            {LABELS[s]}
          </Typography>
        ))}
      </Stack>
    </Box>
  );
}

export default function FoodOrderTrack() {
  const { code } = useParams();
  const navigate = useNavigate();
  const { callApi } = useApi();
  const [order, setOrder] = useState(null);
  const [phone, setPhone] = useState('');
  const [needPhone, setNeedPhone] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchOrder = useCallback(async (ph) => {
    setLoading(true);
    const params = {};
    if (ph) params.phone = ph;
    const res = await callApi({ url: `food/orders/${code}/`, method: 'GET', params });
    setLoading(false);
    if (res?.status === 200) { setOrder(res.data.data); setNeedPhone(false); }
    else if (res?.status === 404 && !ph) setNeedPhone(true);
  }, [code]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { fetchOrder(); }, [fetchOrder]);

  useEffect(() => {
    if (!order || ['DELIVERED', 'CANCELLED'].includes(order.status)) return undefined;
    const t = setInterval(() => fetchOrder(phone), 15000);
    return () => clearInterval(t);
  }, [order, phone, fetchOrder]);

  if (needPhone) {
    return (
      <Box sx={{ maxWidth: 400, mx: 'auto', py: 6, textAlign: 'center' }}>
        <Box sx={{ fontSize: 48, mb: 1 }}>🔒</Box>
        <Typography variant="h6" sx={{ mb: 0.5 }}>Track order {code}</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>Enter the phone number used at checkout.</Typography>
        <Stack direction="row" spacing={1}>
          <TextField size="small" label="Phone" value={phone} onChange={(e) => setPhone(e.target.value)} fullWidth />
          <Button variant="contained" onClick={() => fetchOrder(phone)}>View</Button>
        </Stack>
      </Box>
    );
  }
  if (loading || !order) return <Box sx={{ textAlign: 'center', py: 10 }}><CircularProgress color="primary" /></Box>;

  const activeStep = order.status === 'CANCELLED' ? -1 : STEPS.indexOf(order.status);
  const delivered = order.status === 'DELIVERED';

  return (
    <Box sx={{ maxWidth: 620, mx: 'auto' }}>
      <Card component={motion.div} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
        sx={{ p: { xs: 2.5, md: 3 }, mb: 2.5, textAlign: 'center', overflow: 'visible',
              background: `linear-gradient(180deg, #FFF6EC, #FFFFFF)` }}>
        <Typography variant="overline" color="text.secondary">Order {order.order_code}</Typography>
        <Typography variant="h4" sx={{ mb: 0.5 }}>
          {delivered ? 'Delivered 🎉' : order.status === 'CANCELLED' ? 'Cancelled' : `Arriving in ~${order.eta_minutes} min`}
        </Typography>
        <Typography color="text.secondary">{order.restaurant_name}</Typography>
        {order.status !== 'CANCELLED' && <DeliveryTrack activeStep={activeStep} />}
        {order.status === 'CANCELLED' && (
          <Typography color="error" sx={{ mt: 2, fontWeight: 700 }}>This order was cancelled.</Typography>
        )}
      </Card>

      <Card sx={{ p: 2.5 }}>
        <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1.5 }}>
          <ReceiptLongRoundedIcon color="action" />
          <Typography sx={{ fontWeight: 800 }}>Order summary</Typography>
        </Stack>
        {order.items.map((it) => (
          <Stack key={it.id} direction="row" justifyContent="space-between" sx={{ mb: 1 }}>
            <Typography variant="body2">{it.quantity}× {it.item_name}</Typography>
            <Typography variant="body2" fontWeight={600}>৳{it.line_total}</Typography>
          </Stack>
        ))}
        <Divider sx={{ my: 1 }} />
        <Stack direction="row" justifyContent="space-between">
          <Typography fontWeight={800}>Total (COD)</Typography>
          <Typography fontWeight={800} color="primary.main">৳{order.total}</Typography>
        </Stack>
      </Card>

      <Button fullWidth variant="text" sx={{ mt: 2, color: 'text.secondary' }} onClick={() => navigate('/food')}>
        Order something else
      </Button>
    </Box>
  );
}
