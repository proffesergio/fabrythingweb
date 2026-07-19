import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { Box, Typography, Card, Stepper, Step, StepLabel, Divider, Stack, TextField, Button, CircularProgress } from '@mui/material';
import useApi from '../../hooks/APIHandler';

const STEPS = ['PLACED', 'CONFIRMED', 'PREPARING', 'OUT_FOR_DELIVERY', 'DELIVERED'];
const LABELS = {
  PLACED: 'Placed', CONFIRMED: 'Confirmed', PREPARING: 'Preparing',
  OUT_FOR_DELIVERY: 'On the way', DELIVERED: 'Delivered',
};

export default function FoodOrderTrack() {
  const { code } = useParams();
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
      <Box sx={{ maxWidth: 400, mx: 'auto', py: 6 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>Enter your phone to view order {code}</Typography>
        <Stack direction="row" spacing={1}>
          <TextField size="small" label="Phone" value={phone} onChange={(e) => setPhone(e.target.value)} fullWidth />
          <Button variant="contained" onClick={() => fetchOrder(phone)}>View</Button>
        </Stack>
      </Box>
    );
  }
  if (loading || !order) return <Box sx={{ textAlign: 'center', py: 8 }}><CircularProgress /></Box>;

  const activeStep = order.status === 'CANCELLED' ? -1 : STEPS.indexOf(order.status);

  return (
    <Box sx={{ maxWidth: 640, mx: 'auto' }}>
      <Typography variant="h5">Order {order.order_code}</Typography>
      <Typography color="text.secondary" sx={{ mb: 3 }}>{order.restaurant_name} · ETA ~{order.eta_minutes} min</Typography>
      {order.status === 'CANCELLED' ? (
        <Typography color="error">This order was cancelled.</Typography>
      ) : (
        <Stepper activeStep={activeStep} alternativeLabel sx={{ mb: 3 }}>
          {STEPS.map((s) => <Step key={s}><StepLabel>{LABELS[s]}</StepLabel></Step>)}
        </Stepper>
      )}
      <Card sx={{ p: 2 }}>
        {order.items.map((it) => (
          <Stack key={it.id} direction="row" justifyContent="space-between" sx={{ mb: 1 }}>
            <Typography>{it.quantity}× {it.item_name}</Typography>
            <Typography>৳{it.line_total}</Typography>
          </Stack>
        ))}
        <Divider sx={{ my: 1 }} />
        <Stack direction="row" justifyContent="space-between">
          <Typography>Total (COD)</Typography>
          <Typography fontWeight={700}>৳{order.total}</Typography>
        </Stack>
      </Card>
    </Box>
  );
}
