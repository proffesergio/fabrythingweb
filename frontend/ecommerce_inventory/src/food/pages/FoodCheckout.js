import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import {
  Box, Typography, TextField, Button, Card, Stack, Divider, MenuItem, Alert, InputAdornment,
  Grid, Chip, FormControlLabel, Switch,
} from '@mui/material';
import PersonOutlineRoundedIcon from '@mui/icons-material/PersonOutlineRounded';
import PhoneOutlinedIcon from '@mui/icons-material/PhoneOutlined';
import PlaceOutlinedIcon from '@mui/icons-material/PlaceOutlined';
import MyLocationRoundedIcon from '@mui/icons-material/MyLocationRounded';
import LocalOfferRoundedIcon from '@mui/icons-material/LocalOfferRounded';
import { motion } from 'framer-motion';
import { toast } from 'react-toastify';
import useApi from '../../hooks/APIHandler';
import { useFoodLocation } from '../context/FoodLocationContext';
import {
  selectFoodCart, selectFoodSubtotal, selectFoodRestaurant, selectFoodTip, clearFoodCart,
} from '../redux/foodCartSlice';
import { FOOD } from '../theme';

const rise = { initial: { opacity: 0, y: 14 }, animate: { opacity: 1, y: 0 } };
const METHODS = [
  { key: 'COD', label: 'Cash on Delivery', emoji: '💵' },
  { key: 'BKASH', label: 'bKash', emoji: '📱' },
  { key: 'NAGAD', label: 'Nagad', emoji: '📲' },
  { key: 'QR', label: 'Bangla QR', emoji: '🏷️' },
];

function SectionTitle({ children }) {
  return (
    <Box sx={{ mb: 1.5 }}>
      <Typography variant="h6">{children}</Typography>
      <Box sx={{ width: 36, height: 3, borderRadius: 2, bgcolor: 'primary.main', mt: 0.5 }} />
    </Box>
  );
}

export default function FoodCheckout() {
  const items = useSelector(selectFoodCart);
  const subtotal = useSelector(selectFoodSubtotal);
  const restaurant = useSelector(selectFoodRestaurant);
  const tip = useSelector(selectFoodTip);
  const { zoneId, zones, coords, detectLocation } = useFoodLocation() || {};
  const { callApi, loading } = useApi();
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: '', phone: '', address: '' });
  const [zone, setZone] = useState(zoneId || '');
  const [err, setErr] = useState('');
  const [method, setMethod] = useState('COD');
  const [coupon, setCoupon] = useState('');
  const [applied, setApplied] = useState(null); // { code, discount }
  const [points, setPoints] = useState(0);
  const [redeem, setRedeem] = useState(false);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  useEffect(() => {
    if (!localStorage.getItem('token')) return;
    (async () => {
      const res = await callApi({ url: 'food/loyalty/', method: 'GET', silent: true });
      if (res?.status === 200) setPoints(res.data.data.points || 0);
    })();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const applyCoupon = async () => {
    if (!coupon.trim()) return;
    const res = await callApi({ url: 'food/coupons/validate/', method: 'POST', silent: true,
      body: { code: coupon, restaurant_slug: restaurant.slug, subtotal } });
    const d = res?.data?.data;
    if (d?.valid) { setApplied({ code: d.code, discount: Number(d.discount) }); toast.success(`Coupon applied — ৳${d.discount} off`); }
    else { setApplied(null); toast.error(d?.message || 'Invalid coupon'); }
  };

  const pointsOff = redeem ? Math.min(points, Math.max(0, subtotal - (applied?.discount || 0))) : 0;
  const estTotal = Math.max(0, subtotal - (applied?.discount || 0) - pointsOff);

  const submit = async () => {
    setErr('');
    if (!form.name || !form.phone || !form.address) { setErr('Name, phone and address are required.'); return; }
    if (!zone && !coords) { setErr('Choose a delivery area or use your location.'); return; }
    const body = {
      restaurant_slug: restaurant.slug, contact_name: form.name, contact_phone: form.phone,
      delivery_address: form.address, tip, payment_method: method,
      coupon_code: applied?.code || '', redeem_points: redeem ? points : 0,
      items: items.map((i) => ({ item_id: i.itemId, quantity: i.quantity, option_ids: i.selectedOptions.map((o) => o.optionId) })),
    };
    if (zone) body.zone_id = zone;
    else if (coords) { body.lat = coords.lat; body.lng = coords.lng; }
    const res = await callApi({ url: 'food/orders/', method: 'POST', body });
    if (res?.status === 201) {
      const code = res.data.data.order_code;
      try { localStorage.setItem(`food_ph_${code}`, form.phone); } catch { /* ignore */ }
      dispatch(clearFoodCart());
      toast.success('Order placed!');
      navigate(`/food/order/${code}`, { state: { phone: form.phone } });
    } else if (res?.data?.data) {
      setErr(Array.isArray(res.data.data) ? res.data.data.join(' ') : String(res.data.data));
    }
  };

  if (!items.length) {
    return (
      <Box sx={{ textAlign: 'center', py: 10 }}>
        <Box sx={{ fontSize: 56, mb: 1 }}>🧾</Box>
        <Typography color="text.secondary">Your bag is empty.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 560, mx: 'auto', pb: 12 }}>
      <Typography variant="h4" sx={{ mb: 2.5 }}>Checkout</Typography>
      {err && <Alert severity="error" sx={{ mb: 2, borderRadius: 3 }}>{err}</Alert>}

      <Card component={motion.div} {...rise} sx={{ p: 2.5, mb: 2 }}>
        <SectionTitle>Delivery details</SectionTitle>
        <Stack spacing={2}>
          <TextField label="Name" value={form.name} onChange={set('name')} fullWidth
            InputProps={{ startAdornment: <InputAdornment position="start"><PersonOutlineRoundedIcon color="action" /></InputAdornment> }} />
          <TextField label="Phone" value={form.phone} onChange={set('phone')} fullWidth
            InputProps={{ startAdornment: <InputAdornment position="start"><PhoneOutlinedIcon color="action" /></InputAdornment> }} />
          <TextField label="Delivery address" value={form.address} onChange={set('address')} fullWidth multiline rows={2}
            InputProps={{ startAdornment: <InputAdornment position="start" sx={{ alignSelf: 'flex-start', mt: 1.5 }}><PlaceOutlinedIcon color="action" /></InputAdornment> }} />
          <TextField select label="Delivery area" value={zone} onChange={(e) => setZone(e.target.value)} fullWidth>
            <MenuItem value=""><em>Select area</em></MenuItem>
            {(zones || []).map((z) => <MenuItem key={z.id} value={String(z.id)}>{z.name}</MenuItem>)}
          </TextField>
          <Button variant="text" startIcon={<MyLocationRoundedIcon />} sx={{ alignSelf: 'flex-start', color: 'primary.main' }}
            onClick={() => detectLocation && detectLocation().then(() => toast.info('Location detected')).catch(() => toast.error('Could not get location'))}>
            Use my current location
          </Button>
        </Stack>
      </Card>

      <Card component={motion.div} {...rise} transition={{ delay: 0.05 }} sx={{ p: 2.5, mb: 2 }}>
        <SectionTitle>Payment</SectionTitle>
        <Grid container spacing={1}>
          {METHODS.map((m) => (
            <Grid item xs={6} key={m.key}>
              <Box onClick={() => setMethod(m.key)} component={motion.div} whileTap={{ scale: 0.97 }}
                sx={{ cursor: 'pointer', p: 1.5, borderRadius: 3, display: 'flex', alignItems: 'center', gap: 1,
                  border: `2px solid ${method === m.key ? FOOD.primary : FOOD.line}`,
                  bgcolor: method === m.key ? 'rgba(232,69,43,0.06)' : '#fff' }}>
                <Box sx={{ fontSize: 22 }}>{m.emoji}</Box>
                <Typography variant="body2" sx={{ fontWeight: 700 }}>{m.label}</Typography>
              </Box>
            </Grid>
          ))}
        </Grid>
        {method !== 'COD' && (
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            Online payment runs in sandbox mode — no real charge yet.
          </Typography>
        )}
      </Card>

      <Card component={motion.div} {...rise} transition={{ delay: 0.1 }} sx={{ p: 2.5, mb: 2 }}>
        <SectionTitle>Offers</SectionTitle>
        <Stack direction="row" spacing={1}>
          <TextField size="small" fullWidth placeholder="Coupon code" value={coupon}
            onChange={(e) => setCoupon(e.target.value.toUpperCase())}
            InputProps={{ startAdornment: <InputAdornment position="start"><LocalOfferRoundedIcon color="action" /></InputAdornment> }} />
          <Button variant="outlined" onClick={applyCoupon}>Apply</Button>
        </Stack>
        {applied && <Chip sx={{ mt: 1 }} color="success" label={`${applied.code} · ৳${applied.discount} off`} onDelete={() => setApplied(null)} />}
        {points > 0 && (
          <FormControlLabel sx={{ mt: 1, display: 'flex' }}
            control={<Switch checked={redeem} onChange={(e) => setRedeem(e.target.checked)} />}
            label={`Use ${points} loyalty points (৳${points} off)`} />
        )}
      </Card>

      <Card component={motion.div} {...rise} transition={{ delay: 0.15 }} sx={{ p: 2.5, mb: 2 }}>
        <Stack direction="row" justifyContent="space-between" sx={{ mb: 0.5 }}>
          <Typography color="text.secondary">Subtotal</Typography><Typography sx={{ fontWeight: 700 }}>৳{subtotal}</Typography>
        </Stack>
        {applied && (
          <Stack direction="row" justifyContent="space-between" sx={{ mb: 0.5 }}>
            <Typography color="success.main">Coupon ({applied.code})</Typography>
            <Typography color="success.main">−৳{applied.discount}</Typography>
          </Stack>
        )}
        {pointsOff > 0 && (
          <Stack direction="row" justifyContent="space-between" sx={{ mb: 0.5 }}>
            <Typography color="success.main">Loyalty points</Typography><Typography color="success.main">−৳{pointsOff}</Typography>
          </Stack>
        )}
        <Divider sx={{ my: 1 }} />
        <Stack direction="row" justifyContent="space-between">
          <Typography sx={{ fontWeight: 800 }}>Est. total (before delivery)</Typography>
          <Typography sx={{ fontWeight: 800 }}>৳{estTotal}</Typography>
        </Stack>
        <Typography variant="caption" color="text.secondary">Delivery fee is added and the final total is confirmed by the restaurant.</Typography>
      </Card>

      <Box sx={{ position: 'fixed', left: 0, right: 0, bottom: 0, p: 2, zIndex: 1100,
        background: `linear-gradient(180deg, rgba(253,248,243,0), ${FOOD.canvas} 40%)` }}>
        <Box sx={{ maxWidth: 560, mx: 'auto' }}>
          <Button fullWidth variant="contained" size="large" disabled={loading} onClick={submit}
            sx={{ py: 1.6, borderRadius: 999, boxShadow: '0 12px 30px rgba(232,69,43,0.35)' }}>
            {loading ? 'Placing order…' : `Place order · ${METHODS.find((m) => m.key === method)?.label}`}
          </Button>
        </Box>
      </Box>
    </Box>
  );
}
