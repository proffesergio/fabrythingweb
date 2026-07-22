import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { Box, Typography, Card, Divider, Stack, TextField, Button, CircularProgress, Avatar } from '@mui/material';
import ReceiptLongRoundedIcon from '@mui/icons-material/ReceiptLongRounded';
import CallRoundedIcon from '@mui/icons-material/CallRounded';
import TwoWheelerRoundedIcon from '@mui/icons-material/TwoWheelerRounded';
import { motion } from 'framer-motion';
import useApi from '../../hooks/APIHandler';
import LiveTrackMap from '../components/LiveTrackMap';
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
      <Box sx={{ position: 'relative', height: 6, borderRadius: 3, bgcolor: 'divider' }}>
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
                sx={{ width: 16, height: 16, borderRadius: '50%', border: (t) => `3px solid ${done ? t.palette.primary.main : t.palette.divider}`,
                      bgcolor: done ? 'primary.main' : 'background.paper' }} />
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

// How long after the last heartbeat we still call the rider's pin "live". The
// dashboard beats every ~20s, so a minute of silence means they've lost signal
// or closed the app — better to say so than to show a pin frozen in the past.
const PRESENCE_WINDOW_MS = 60 * 1000;

function RiderCard({ order }) {
  const enRoute = order.status === 'OUT_FOR_DELIVERY';
  // The server only sends the pin while OUT_FOR_DELIVERY (LIVE_TRACKING_STATUSES
  // in serializers_orders.py); contact details arrive as soon as one is assigned.
  const hasPin = order.rider_lat != null && order.rider_lng != null;
  const lastSeen = order.rider_last_seen_at ? new Date(order.rider_last_seen_at) : null;
  const stale = !lastSeen || Date.now() - lastSeen.getTime() > PRESENCE_WINDOW_MS;

  return (
    <Card sx={{ p: 2.5, mb: 2.5 }}>
      <Stack direction="row" alignItems="center" spacing={1.5}>
        <Avatar sx={{ bgcolor: 'primary.main', width: 44, height: 44 }}>
          <TwoWheelerRoundedIcon />
        </Avatar>
        <Box sx={{ minWidth: 0, flexGrow: 1 }}>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
            {enRoute ? 'Your rider is on the way' : 'Your rider'}
          </Typography>
          <Typography noWrap sx={{ fontWeight: 800 }}>{order.rider_name}</Typography>
        </Box>
        {order.rider_phone && (
          <Button
            variant="contained" href={`tel:${order.rider_phone}`}
            startIcon={<CallRoundedIcon />}
            sx={{ borderRadius: 999, flexShrink: 0 }}
          >
            Call
          </Button>
        )}
      </Stack>

      {enRoute && (
        <Box sx={{ mt: 2 }}>
          {hasPin ? (
            <>
              <LiveTrackMap
                rider={{ lat: order.rider_lat, lng: order.rider_lng }}
                destination={{ lat: order.delivery_lat, lng: order.delivery_lng }}
              />
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                {stale
                  ? 'Last known position — the rider may have lost signal.'
                  : '🛵 Rider · 🏠 Your address · updates automatically'}
              </Typography>
            </>
          ) : (
            <Typography variant="caption" color="text.secondary">
              Live location isn’t available for this rider right now — call them if you need to.
            </Typography>
          )}
        </Box>
      )}
    </Card>
  );
}

export default function FoodOrderTrack() {
  const { code } = useParams();
  const navigate = useNavigate();
  const { state } = useLocation();
  const { callApi } = useApi();
  const [order, setOrder] = useState(null);
  const [phone, setPhone] = useState(() => localStorage.getItem(`food_ph_${code}`) || (state && state.phone) || '');
  const [needPhone, setNeedPhone] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchOrder = useCallback(async (ph) => {
    setLoading(true);
    const params = {};
    if (ph) params.phone = ph;
    // silent: a 404 here just means "guest order, ask for the phone" — we handle it,
    // so don't fire the global "Order not found" toast.
    const res = await callApi({ url: `food/orders/${code}/`, method: 'GET', params, silent: true });
    setLoading(false);
    if (res?.status === 200 && res.data?.data?.order_code) {
      setOrder(res.data.data);
      setNeedPhone(false);
      if (ph) { try { localStorage.setItem(`food_ph_${code}`, ph); } catch { /* ignore */ } }
    } else {
      // No order returned (guest order without/with-wrong phone) — prompt for it.
      setOrder(null);
      setNeedPhone(true);
    }
  }, [code]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetchOrder(localStorage.getItem(`food_ph_${code}`) || (state && state.phone) || '');
  }, [fetchOrder]); // eslint-disable-line react-hooks/exhaustive-deps

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
              background: (t) => t.palette.mode === 'dark'
                ? `linear-gradient(180deg, ${t.palette.background.paper}, ${t.palette.background.default})`
                : 'linear-gradient(180deg, #FFF6EC, #FFFFFF)' }}>
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

      {/* Shown from assignment onward; the live map only once out for delivery. */}
      {order.rider_name && order.status !== 'CANCELLED' && <RiderCard order={order} />}

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
