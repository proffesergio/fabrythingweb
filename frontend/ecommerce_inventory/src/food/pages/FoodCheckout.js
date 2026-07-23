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
import { isSignedIn } from '../../utils/authToken';
import { useFoodLocation } from '../context/FoodLocationContext';
import {
  selectFoodCart, selectFoodSubtotal, selectFoodRestaurant, selectFoodTip, clearFoodCart,
} from '../redux/foodCartSlice';

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
  const { zoneId, zones, villageId, coords, detectLocation, openPicker } = useFoodLocation() || {};
  const { callApi, loading } = useApi();
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: '', phone: '', address: '' });
  const [zone, setZone] = useState(zoneId || '');
  const [village, setVillage] = useState(villageId || '');
  const [err, setErr] = useState('');
  const [method, setMethod] = useState('COD');
  const [coupon, setCoupon] = useState('');
  const [applied, setApplied] = useState(null); // { code, discount }
  const [points, setPoints] = useState(0);
  const [redeem, setRedeem] = useState(false);
  // Zone ids this restaurant delivers to. null means "offer every zone" — that
  // covers both "still loading" and the server's own null for an unconfigured
  // restaurant, which delivers everywhere (food.services.served_zones).
  const [servedIds, setServedIds] = useState(null);
  // The server's live delivery quote for the current destination. null while we
  // have not asked yet. Quoting through the same endpoint the order is priced
  // by is the whole point — a fee shown here can never differ from the fee
  // charged, and an address beyond range is refused *before* the customer fills
  // in their details rather than by an opaque 400 afterwards.
  const [quote, setQuote] = useState(null);
  const [quoting, setQuoting] = useState(false);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  // Offering an area the restaurant does not serve is what produced the opaque
  // "Could not place order" 400 — the union list must come from the restaurant,
  // not from the global zone list.
  useEffect(() => {
    if (!restaurant?.slug) return;
    (async () => {
      const res = await callApi({ url: `food/restaurants/${restaurant.slug}/`, method: 'GET', silent: true });
      const ids = res?.data?.data?.served_zone_ids;
      if (Array.isArray(ids)) setServedIds(ids.map(String));
    })();
  }, [restaurant?.slug]); // eslint-disable-line react-hooks/exhaustive-deps

  const zoneOptions = (zones || []).filter(
    (z) => !servedIds || servedIds.includes(String(z.id)));

  // The area carried over from the header picker may not be one this restaurant
  // serves; drop it rather than submitting an order the server will reject.
  useEffect(() => {
    if (zone && servedIds && !servedIds.includes(String(zone))) { setZone(''); setVillage(''); }
  }, [servedIds]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    // Loyalty is per-account; an expired token made this 401 on every guest
    // checkout. isSignedIn() also purges the dead token (utils/authToken.js).
    if (!isSignedIn()) return;
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

  // Re-quote whenever the destination moves. The pin wins over the village,
  // which wins over the zone — same precedence the server applies, so the
  // number on screen is the number it will charge.
  useEffect(() => {
    if (!restaurant?.slug || (!zone && !village && !coords)) { setQuote(null); return undefined; }
    let cancelled = false;
    setQuoting(true);
    (async () => {
      const params = { restaurant: restaurant.slug };
      if (zone) params.zone = zone;
      if (village) params.village = village;
      if (coords) { params.lat = coords.lat; params.lng = coords.lng; }
      const res = await callApi({ url: 'food/delivery-quote/', method: 'GET', params, silent: true });
      if (cancelled) return;
      setQuote(res?.data?.data || null);
      setQuoting(false);
    })();
    return () => { cancelled = true; };
  }, [restaurant?.slug, zone, village, coords?.lat, coords?.lng]); // eslint-disable-line react-hooks/exhaustive-deps

  const pointsOff = redeem ? Math.min(points, Math.max(0, subtotal - (applied?.discount || 0))) : 0;
  const foodTotal = Math.max(0, subtotal - (applied?.discount || 0) - pointsOff);
  const deliveryFee = quote?.deliverable ? Number(quote.fee) : 0;
  const grandTotal = foodTotal + deliveryFee + Number(tip || 0);
  // Undeliverable is known before submit, so the button says so rather than
  // letting the customer discover it after filling the whole form.
  const blocked = quote != null && quote.deliverable === false;

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
    if (village) body.village_id = village;
    // Send the pin even when a zone was chosen. The zone decides *whether* we
    // deliver; the pin decides *what it costs*. Omitting it here while the quote
    // above included it would price the order off the zone centre and charge a
    // different fee than the one on screen.
    if (coords) { body.delivery_lat = coords.lat; body.delivery_lng = coords.lng; }
    if (coords?.lat) { body.delivery_lat = coords.lat; body.delivery_lng = coords.lng; }
    // rawError, because callApi returns null on any non-2xx — without it the
    // server's actual reason ("This restaurant does not deliver to the selected
    // area", "Minimum order is BDT 100"…) was dropped and the customer only ever
    // saw a generic failure toast with nothing to act on.
    // silent too: we render the precise reason in the Alert above, so the generic
    // toast would only be a duplicate that says less.
    const res = await callApi({ url: 'food/orders/', method: 'POST', body, rawError: true, silent: true });
    if (res?.status === 201) {
      const code = res.data.data.order_code;
      try { localStorage.setItem(`food_ph_${code}`, form.phone); } catch { /* ignore */ }
      dispatch(clearFoodCart());
      toast.success('Order placed!');
      navigate(`/food/order/${code}`, { state: { phone: form.phone } });
      return;
    }
    // Error envelope is {errors, field_errors, message} — NOT {data}. `data` is
    // only present on 2xx (see core.helpers.renderResponse).
    const d = res?.data || {};
    const reasons = d.errors || d.data;
    setErr(Array.isArray(reasons) ? reasons.join(' ')
      : reasons ? String(reasons)
      : d.message || 'Could not place order. Please try again.');
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
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
            <TextField select label="Union" value={zone} fullWidth
              onChange={(e) => { setZone(e.target.value); setVillage(''); }}>
              <MenuItem value=""><em>Select union</em></MenuItem>
              {zoneOptions.map((z) => <MenuItem key={z.id} value={String(z.id)}>{z.name}</MenuItem>)}
            </TextField>
            <TextField select label="Village" value={village} fullWidth
              disabled={!zoneOptions.find((z) => String(z.id) === String(zone))?.villages?.length}
              onChange={(e) => setVillage(e.target.value)}>
              <MenuItem value=""><em>Optional</em></MenuItem>
              {(zoneOptions.find((z) => String(z.id) === String(zone))?.villages || [])
                .map((v) => <MenuItem key={v.id} value={String(v.id)}>{v.name}</MenuItem>)}
            </TextField>
          </Stack>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Button variant="text" startIcon={<MyLocationRoundedIcon />} sx={{ color: 'primary.main' }}
              onClick={() => detectLocation && detectLocation().then(() => toast.info('Location detected')).catch(() => toast.error('Could not get location'))}>
              Use my location
            </Button>
            {openPicker && (
              <Button variant="text" startIcon={<PlaceOutlinedIcon />} sx={{ color: 'text.secondary' }} onClick={openPicker}>
                {coords?.lat ? `Pin set (${coords.lat.toFixed(3)}, ${coords.lng.toFixed(3)})` : 'Drop a map pin'}
              </Button>
            )}
          </Stack>
        </Stack>
      </Card>

      <Card component={motion.div} {...rise} transition={{ delay: 0.05 }} sx={{ p: 2.5, mb: 2 }}>
        <SectionTitle>Payment</SectionTitle>
        <Grid container spacing={1}>
          {METHODS.map((m) => (
            <Grid item xs={6} key={m.key}>
              <Box onClick={() => setMethod(m.key)} component={motion.div} whileTap={{ scale: 0.97 }}
                sx={{ cursor: 'pointer', p: 1.5, borderRadius: 3, display: 'flex', alignItems: 'center', gap: 1,
                  border: (t) => `2px solid ${method === m.key ? t.palette.primary.main : t.palette.divider}`,
                  bgcolor: method === m.key ? 'rgba(232,69,43,0.06)' : 'background.paper' }}>
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
        <Stack direction="row" justifyContent="space-between" sx={{ mb: 0.5 }}>
          <Typography color="text.secondary">
            Delivery
            {quote?.distance_km && (
              <Typography component="span" variant="caption" color="text.secondary">
                {' '}· {quote.distance_km} km
              </Typography>
            )}
          </Typography>
          <Typography sx={{ fontWeight: 700 }}>
            {quoting ? '…' : quote?.deliverable ? `৳${quote.fee}` : '—'}
          </Typography>
        </Stack>
        {Number(tip) > 0 && (
          <Stack direction="row" justifyContent="space-between" sx={{ mb: 0.5 }}>
            <Typography color="text.secondary">Tip</Typography>
            <Typography sx={{ fontWeight: 700 }}>৳{tip}</Typography>
          </Stack>
        )}
        <Divider sx={{ my: 1 }} />
        <Stack direction="row" justifyContent="space-between">
          <Typography sx={{ fontWeight: 800 }}>Total</Typography>
          <Typography sx={{ fontWeight: 800 }}>৳{grandTotal}</Typography>
        </Stack>
        {blocked ? (
          <Alert severity="warning" sx={{ mt: 1.5, borderRadius: 2 }}>{quote.reason}</Alert>
        ) : (
          <Typography variant="caption" color="text.secondary">
            {quote?.priced_by === 'distance'
              ? 'Delivery is priced by distance from the restaurant.'
              : 'Delivery fee is confirmed when the restaurant accepts your order.'}
            {/* A zone-centre distance can be a couple of km out inside a large
                union, and the customer pays for that imprecision — so ask. */}
            {quote?.distance_source === 'zone' && ' Drop a pin for an exact fee.'}
          </Typography>
        )}
      </Card>

      <Box sx={{ position: 'fixed', left: 0, right: 0, bottom: 0, p: 2, zIndex: 1100,
        background: (t) => `linear-gradient(180deg, transparent, ${t.palette.background.default} 40%)` }}>
        <Box sx={{ maxWidth: 560, mx: 'auto' }}>
          <Button
            component={motion.button}
            // Transform-only animation (the sweep is a moving gradient, the press
            // is a scale) so it stays cheap on the low-end phones this is built
            // for — nothing here triggers layout.
            whileHover={{ scale: 1.015 }}
            whileTap={{ scale: 0.985 }}
            transition={{ type: 'spring', stiffness: 420, damping: 26 }}
            fullWidth variant="contained" size="large" disabled={loading || blocked} onClick={submit}
            sx={{
              py: 1.6, borderRadius: 999, position: 'relative', overflow: 'hidden',
              // No hardcoded boxShadow here: it used to sit at a bigger blur than
              // the theme's hover shadow, so hovering made the glow *shrink*.
              // Let the theme own both states.
              '&::after': loading ? {} : {
                content: '""', position: 'absolute', inset: 0,
                background: 'linear-gradient(100deg, transparent 20%, rgba(255,255,255,0.28) 50%, transparent 80%)',
                transform: 'translateX(-100%)',
                animation: 'placeOrderSheen 2.6s ease-in-out infinite',
              },
              '@keyframes placeOrderSheen': {
                '0%': { transform: 'translateX(-100%)' },
                '60%, 100%': { transform: 'translateX(100%)' },
              },
              '@media (prefers-reduced-motion: reduce)': { '&::after': { animation: 'none' } },
            }}
          >
            {loading ? 'Placing order…'
              : blocked ? 'Address outside delivery range'
              : `Place order · ৳${grandTotal} · ${METHODS.find((m) => m.key === method)?.label}`}
          </Button>
        </Box>
      </Box>
    </Box>
  );
}
